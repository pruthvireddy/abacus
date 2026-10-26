"""Build bounded selected web reports from saved Study 22 CSV evidence only."""
from __future__ import annotations

import csv
from datetime import datetime, timezone
import hashlib
import html
import json
from pathlib import Path

LABELS = {"all_hours": "All hours", "asia": "Asia", "london": "London", "ny": "NY",
          "asia_open": "Asia Open", "ny_open": "NY Open", "ny_am": "NY AM", "ny_pm": "NY PM"}
DIRECTIONS = {"bullish": "Bullish", "bearish": "Bearish", "all": "Both directions"}
STAT_COLUMNS = [
    ("exact_trends", "Exact trends", 0), ("mean_candles", "Mean", 2),
    ("median_candles", "Median", 2), ("mode_candles", "Mode", 0),
    ("q25_candles", "Q25", 2), ("q75_candles", "Q75", 2),
    ("p90_candles", "P90", 2), ("p95_candles", "P95", 2),
    ("max_candles", "Maximum", 0), ("censored_trends", "Censored", 0),
]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=None if path.name == "publication.json" else 2,
                  separators=(",", ":") if path.name == "publication.json" else None,
                  allow_nan=False)
        stream.write("\n")


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        return list(reader.fieldnames or ()), list(reader)


def number(raw: str) -> int | float | None:
    if raw == "":
        return None
    value = float(raw)
    # Exact saved strings remain in CSV; retain more than the displayed precision.
    return int(value) if value.is_integer() else round(value, 6)


def build_reports(stage: Path) -> None:
    settings = json.loads((stage / "config.json").read_text())
    run_id = stage.name
    paths = {name: stage / "tables" / filename for name, filename in (
        ("summary", "trend_summary.csv"), ("histogram", "trend_histogram.csv"),
        ("survival", "trend_survival.csv"),
    )}
    tables = {name: read_csv(path) for name, path in paths.items()}
    source_hashes = {path.relative_to(stage).as_posix(): sha(path) for path in paths.values()}
    saved_rows = {path.relative_to(stage).as_posix(): tables[name][1] for name, path in paths.items()}
    audit_payload = json.loads((stage / "input-audit.json").read_text())
    audits = ({int(key): value for key, value in audit_payload["settings"].items()}
              if isinstance(audit_payload, dict) else {entry["setting_ticks"]: entry for entry in audit_payload})
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    all_bindings = []
    result_summaries = []
    for setting in (4, 5, 6):
        target = stage / "publications" / f"{setting}t"
        if target.exists():
            raise FileExistsError("selected publication source already exists")
        target.mkdir(parents=True)
        bindings = []
        summary = [(i + 2, row) for i, row in enumerate(tables["summary"][1]) if row["setting_ticks"] == str(setting)]
        def table(section_id, title, selected, context_keys):
            columns = [{"key": key, "label": label} for key, label in context_keys]
            columns += [{"key": key.removesuffix("_candles").removesuffix("_trends"), "label": label, "format": "number", "precision": precision,
                         **({"unit": "candles"} if key.endswith("_candles") else {})}
                        for key, label, precision in STAT_COLUMNS]
            rows = []
            for row_number, source in selected:
                row = {}
                for key, _label in context_keys:
                    value = (DIRECTIONS[source["direction"]] if key == "direction"
                             else LABELS[source["timeframe_id"]] if key == "timeframe"
                             else source["year"] + (" (partial)" if source["year"] in ("2019", "2026") else ""))
                    row[key] = value
                for key, _label, _precision in STAT_COLUMNS:
                    report_key = key.removesuffix("_candles").removesuffix("_trends")
                    row[report_key] = number(source[key])
                    bindings.append({"section": section_id, "report_row": len(rows), "column": report_key,
                                     "source": "tables/trend_summary.csv", "source_row": row_number,
                                     "source_column": key, "original": source[key], "value": row[report_key]})
                rows.append(row)
            return {"id": section_id, "kind": "table", "title": title,
                    "description": "Lengths in candles, conditional on fully observed trend starts and ends. Censored counts are excluded from length estimates.",
                    "notes": ["Trend = consecutive completed candles with the same close-open sign. Dojis break the run.",
                              "Groups use the first candle's opening time. The full run is retained across named window boundaries.",
                              "Mode shows the smallest tied value; all ties are retained in the summary CSV. Empty estimates are not available."],
                    "columns": columns, "rows": rows, "referenceIds": ["summary-source"]}
        overall = [(i, r) for i, r in summary if r["year"] == "" and r["timeframe_id"] == "all_hours"]
        audit = audits[setting]
        sections = [{"id": "definition", "kind": "text", "title": "What is measured",
                     "body": f"ES {setting}-tick Range XV. A bullish trend is consecutive completed candles with close above open; a bearish trend uses close below open. A doji ends a trend. Length counts candles, not minutes. Exact lengths require an observed start and an observed opposite/doji breaker. Boundary-limited runs are shown as censored. These are descriptive chart statistics, not a trading result."},
                    {"id": "coverage", "kind": "metrics", "title": "Observed coverage",
                     "items": [{"label": "Input candles", "value": audit["input_rows"], "format": "number", "precision": 0},
                               {"label": "Eligible completed candles", "value": audit["primary_eligible_bars"], "format": "number", "precision": 0},
                               {"label": "Eligible dojis", "value": audit["doji_eligible_bars"], "format": "number", "precision": 0},
                               {"label": "Covered sessions", "value": number(overall[0][1]["covered_sessions"]), "format": "number", "precision": 0}]},
                    table("overall", "Overall trend lengths", overall, [("direction", "Direction")])]
        result_summaries.append({"setting_ticks": setting, "overall": [r for _i, r in overall]})
        # Ten exact-length bins and five empirical tails, selected by direction.
        for name, title, index_key, index_label in (
            ("histogram", "Overall length distribution", "bin", "Length (candles)"),
            ("survival", "Overall share reaching a length", "minimum_candles", "At least (candles)"),
        ):
            selected = [(i + 2, r) for i, r in enumerate(tables[name][1]) if r["setting_ticks"] == str(setting) and r["year"] == "" and r["timeframe_id"] == "all_hours" and r["direction"] != "all"]
            rows = []
            for row_number, source in selected:
                row = {"direction": DIRECTIONS[source["direction"]], "length": source[index_key],
                       "count": number(source["numerator"]), "denominator": number(source["denominator"]),
                       "share": number(source["probability"])}
                rows.append(row)
                for key, source_key in (("count", "numerator"), ("denominator", "denominator"), ("share", "probability")):
                    bindings.append({"section": name, "report_row": len(rows) - 1, "column": key,
                                     "source": paths[name].relative_to(stage).as_posix(), "source_row": row_number,
                                     "source_column": source_key, "original": source[source_key], "value": row[key]})
            sections.append({"id": name, "kind": "table", "title": title,
                             "description": "Empirical fractions among exact, uncensored trends. Complete overall/year/window distributions are included in the selected CSV downloads.",
                             "columns": [{"key": "direction", "label": "Direction"}, {"key": "length", "label": index_label},
                                         {"key": "count", "label": "Trends", "format": "number", "precision": 0},
                                         {"key": "denominator", "label": "Exact denominator", "format": "number", "precision": 0},
                                         {"key": "share", "label": "Share", "format": "percent", "precision": 2}], "rows": rows})
        sections += [table("yearly", "Yearly trend lengths", [(i, r) for i, r in summary if r["year"] and r["timeframe_id"] == "all_hours" and r["direction"] != "all"], [("year", "Session year"), ("direction", "Direction")]),
                     table("timeframes", "Session and timeframe trend lengths", [(i, r) for i, r in summary if r["year"] == "" and r["timeframe_id"] != "all_hours" and r["direction"] != "all"], [("timeframe", "Window"), ("direction", "Direction")])]
        for direction in ("bullish", "bearish"):
            sections.append(table("yearly-" + direction, "Year by session — " + DIRECTIONS[direction],
                                  [(i, r) for i, r in summary if r["year"] and r["timeframe_id"] != "all_hours" and r["direction"] == direction],
                                  [("year", "Session year"), ("timeframe", "Window")]))
        # Frequency and tail tables carry every requested section, not just totals.
        for direction in ("bullish", "bearish"):
            for scope, title in (("year", "Yearly"), ("window", "Session / timeframe"), ("year-window", "Year by session")):
                section_id = f"distribution-{scope}-{direction}"
                selected = [(i + 2, r) for i, r in enumerate(tables["histogram"][1])
                            if r["setting_ticks"] == str(setting) and r["direction"] == direction
                            and ((scope == "year" and r["year"] and r["timeframe_id"] == "all_hours")
                                 or (scope == "window" and not r["year"] and r["timeframe_id"] != "all_hours")
                                 or (scope == "year-window" and r["year"] and r["timeframe_id"] != "all_hours"))]
                grouped = {}
                for line, source in selected:
                    key = (source["year"], source["timeframe_id"])
                    if key not in grouped:
                        context = (source["year"] + ("*" if source["year"] in ("2019", "2026") else ""))
                        if scope != "year":
                            context = (context + " · " if context else "") + LABELS[source["timeframe_id"]]
                        grouped[key] = {"context": context, "denominator": number(source["denominator"])}
                    if source["bin"] == settings["trend_definition"]["histogram_bins"][0]:
                        bindings.append({"section": section_id, "report_row": list(grouped).index(key), "column": "denominator",
                                         "source": "tables/trend_histogram.csv", "source_row": line,
                                         "source_column": "denominator", "original": source["denominator"], "value": grouped[key]["denominator"]})
                    column = "b" + str(settings["trend_definition"]["histogram_bins"].index(source["bin"]))
                    grouped[key][column] = number(source["probability"])
                    bindings.append({"section": section_id, "report_row": list(grouped).index(key), "column": column,
                                     "source": "tables/trend_histogram.csv", "source_row": line,
                                     "source_column": "probability", "original": source["probability"], "value": grouped[key][column]})
                bins = settings["trend_definition"]["histogram_bins"]
                sections.append({"id": section_id, "kind": "table", "title": title + " length distribution — " + DIRECTIONS[direction],
                                 "description": "Each length column is the share of exact trends in that bin. Unrounded rows sum to 100%; displayed rounding may differ slightly. * marks a partial coverage year.",
                                 "columns": [{"key": "context", "label": "Year / window"}, {"key": "denominator", "label": "Exact trends", "format": "number", "precision": 0},
                                             *[{"key": "b" + str(i), "label": label + " candles", "format": "percent", "precision": 1} for i, label in enumerate(bins)]],
                                 "rows": list(grouped.values())})
                section_id = f"tails-{scope}-{direction}"
                selected = [(i + 2, r) for i, r in enumerate(tables["survival"][1])
                            if r["setting_ticks"] == str(setting) and r["direction"] == direction
                            and ((scope == "year" and r["year"] and r["timeframe_id"] == "all_hours")
                                 or (scope == "window" and not r["year"] and r["timeframe_id"] != "all_hours")
                                 or (scope == "year-window" and r["year"] and r["timeframe_id"] != "all_hours"))]
                grouped = {}
                for line, source in selected:
                    key = (source["year"], source["timeframe_id"])
                    if key not in grouped:
                        context = source["year"] + ("*" if source["year"] in ("2019", "2026") else "")
                        if scope != "year":
                            context = (context + " · " if context else "") + LABELS[source["timeframe_id"]]
                        grouped[key] = {"context": context, "denominator": number(source["denominator"])}
                    if source["minimum_candles"] == str(settings["trend_definition"]["survival_thresholds"][0]):
                        bindings.append({"section": section_id, "report_row": list(grouped).index(key), "column": "denominator",
                                         "source": "tables/trend_survival.csv", "source_row": line,
                                         "source_column": "denominator", "original": source["denominator"], "value": grouped[key]["denominator"]})
                    column = "ge" + source["minimum_candles"]
                    grouped[key][column] = number(source["probability"])
                    bindings.append({"section": section_id, "report_row": list(grouped).index(key), "column": column,
                                     "source": "tables/trend_survival.csv", "source_row": line,
                                     "source_column": "probability", "original": source["probability"], "value": grouped[key][column]})
                sections.append({"id": section_id, "kind": "table", "title": title + " share reaching a length — " + DIRECTIONS[direction],
                                 "description": "Empirical share with length at least the stated number of candles among exact trends. * marks a partial coverage year.",
                                 "columns": [{"key": "context", "label": "Year / window"}, {"key": "denominator", "label": "Exact trends", "format": "number", "precision": 0},
                                             *[{"key": "ge" + str(k), "label": "≥ " + str(k) + " candles", "format": "percent", "precision": 1} for k in settings["trend_definition"]["survival_thresholds"]]],
                                 "rows": list(grouped.values())})
        sections.append({"id": "methods", "kind": "text", "title": "Windows, boundaries and data limits",
                         "body": "All clock windows use inferred America/New_York wall time, including seasonal clock changes. Start included; end excluded. Asia 20:00–02:00; London 02:00–09:00; NY 09:30–16:00; Asia Open 19:30–21:30; NY Open 09:30–10:30; NY AM 10:30–12:30; NY PM 12:30–16:00. Windows overlap independently, so their counts cannot all be added. Unassigned clock hours remain in all-hours totals. Year follows the inferred 18:00 trading-session date. 2019 and 2026 are partial coverage years. The entire partial final session, September 24, 2026, is excluded. Unknown session-end bar completion breaks continuity; trends never stitch across sessions. Exact-length estimates are conditional on uncensored runs; they may differ from boundary-limited runs. Same-second candles and identical rows retain source order. OHLC is available and volume is absent; exact last-trade timing and contract/roll treatment are unverified. No population confidence intervals or predictive trading claims are made."})
        downloads = []
        for name, direction, filename, label in (
            ("summary", None, "trend-summary.csv", "All trend-length summaries"),
            ("histogram", "bullish", "bullish-length-distribution.csv", "Bullish length distributions"),
            ("histogram", "bearish", "bearish-length-distribution.csv", "Bearish length distributions"),
            ("survival", "directional", "directional-length-shares.csv", "Directional length thresholds"),
        ):
            columns = [c for c in tables[name][0] if c != "units"]
            selected = [(i + 2, r) for i, r in enumerate(tables[name][1]) if r["setting_ticks"] == str(setting) and (direction is None or r["direction"] == direction or direction == "directional" and r["direction"] != "all")]
            path = target / "downloads" / filename
            path.parent.mkdir(exist_ok=True)
            with path.open("x", newline="", encoding="utf-8") as stream:
                writer = csv.DictWriter(stream, fieldnames=columns)
                writer.writeheader()
                writer.writerows({c: row[c] for c in columns} for _i, row in selected)
            _header, copied = read_csv(path)
            if copied != [{c: r[c] for c in columns} for _i, r in selected]:
                raise ValueError("selected CSV string projection differs from saved evidence")
            bindings.append({"download": filename, "source": paths[name].relative_to(stage).as_posix(),
                             "source_rows": [i for i, _r in selected], "columns": columns,
                             "sha256": sha(path), "original_strings_verified": True})
            downloads.append({"id": filename.removesuffix(".csv"), "path": "downloads/" + filename,
                              "label": label, "description": "Exact saved CSV strings for all overall, yearly, named-window and year-by-window cells; blank estimates are undefined.",
                              "population": "Fully observed directional trends; censored counts retained separately in summaries.",
                              "units": "Lengths in candles; probabilities are ratios; counts are trends or covered sessions/bars as labelled.",
                              "scope": f"ES {setting}t, observed 2019–2026 history; final partial session excluded. " + ("Bullish and bearish directions." if direction == "directional" else (DIRECTIONS[direction] + "." if direction else "Bullish, bearish and combined directions.")),
                              "mediaType": "text/csv", "sha256": sha(path), "rowCount": len(selected), "columns": columns,
                              "source": {"runId": run_id, "artifact": paths[name].relative_to(stage).as_posix(), "sha256": sha(paths[name])}})
        report = {"schemaVersion": "1.1", "id": f"es-range-xv-trend-length-{setting}t-20261012",
                  "title": f"ES {setting} RXV · Directional trend lengths",
                  "summary": "How many candles form each bullish and bearish trend? Overall, annual, session and annual-by-session evidence from the 2019–2026 ES Range XV export.",
                  "publishedAt": timestamp, "source": {"producer": "sahadeva", "runId": run_id},
                  "sections": sections, "downloads": downloads,
                  "references": [{"id": "summary-source", "kind": "saved-artifact", "label": "Saved trend-length summaries", "title": "Complete grouped descriptive summary table", "runId": run_id, "artifact": "tables/trend_summary.csv", "sha256": sha(paths["summary"])}],
                  "notes": ["A candle-colour trend is defined by consecutive close-open signs. It does not imply a swing trend or a tradable edge.", "Trend lengths use complete starts/ends; first and terminal runs in each segment can be censored."]}
        for binding in bindings:
            if "section" not in binding:
                continue
            original = saved_rows[binding["source"]][binding["source_row"] - 2][binding["source_column"]]
            section = next(s for s in sections if s["id"] == binding["section"])
            value = section["rows"][binding["report_row"]][binding["column"]]
            if original != binding["original"] or number(original) != value:
                raise ValueError("public table cell disagrees with saved evidence")
        if any(sha(stage / locator) != expected for locator, expected in source_hashes.items()):
            raise ValueError("saved source table changed during report preparation")
        write_json(target / "publication.json", report)
        metric_bindings = [{"section": "coverage", "item": i, "source": "input-audit.json",
                            "setting_ticks": setting, "source_key": key, "value": audit[key]}
                           for i, key in enumerate(("input_rows", "primary_eligible_bars", "doji_eligible_bars"))]
        metric_bindings.append({"section": "coverage", "item": 3, "source": "tables/trend_summary.csv",
                                "source_row": overall[0][0], "source_key": "covered_sessions",
                                "value": number(overall[0][1]["covered_sessions"])})
        for item in metric_bindings:
            if sections[1]["items"][item["item"]]["value"] != item["value"]:
                raise ValueError("coverage metric transfer mismatch")
        write_json(target / "source-map.json", {"run_id": run_id, "setting_ticks": setting, "bindings": bindings, "metric_bindings": metric_bindings,
                                              "numeric_projection": "Noninteger public values rounded to six decimals, exceeding displayed precision; downloads preserve original strings.",
                                              "source_hashes": source_hashes})
        write_json(target / "verification.json", {"result": "passed", "run_id": run_id, "setting_ticks": setting,
                                                 "numeric_cells_checked": sum("section" in b for b in bindings) + len(metric_bindings),
                                                 "csv_files_checked": len(downloads), "publication_sha256": sha(target / "publication.json")})
        all_bindings.append({"setting_ticks": setting, "publication": (target / "publication.json").relative_to(stage).as_posix(), "sha256": sha(target / "publication.json")})
    write_json(stage / "publication-verification.json", {"result": "passed", "run_id": run_id, "publications": all_bindings,
                                                       "artifact_hashes": {p.relative_to(stage).as_posix(): sha(p) for p in [*paths.values(), stage / "tables" / "coverage.csv", stage / "input-audit.json", *sorted((stage / "publications").rglob("*"))] if p.is_file()},
                                                       "scope": "All selected numeric cells and CSV strings compared with saved source tables; source table hashes retained. No numerical rerun."})
    lines = ["# ES Range XV directional trend lengths", "", "Protocol 0.2.0. Length = consecutive same-sign close-open completed candles. Exact lengths exclude unknown starts/ends. Group by first candle opening; no named-window truncation.", "", "| Chart | Direction | Exact trends | Mean candles | Median | P90 | Maximum | Censored |", "|---|---|---:|---:|---:|---:|---:|---:|"]
    for result in result_summaries:
        for row in result["overall"]:
            lines.append("| " + " | ".join([str(result["setting_ticks"]), DIRECTIONS[row["direction"]], *[row[k] for k in ("exact_trends", "mean_candles", "median_candles", "p90_candles", "max_candles", "censored_trends")]]) + " |")
    lines += ["", "All overall/yearly/session/year-by-session summaries, distributions and thresholds are retained in tables/. The partial final session is excluded. 2019/2026 are partial coverage years. New York clock and completion are inferred; volume and contract/roll treatment are unverified. These descriptive statistics do not establish profitability."]
    with (stage / "report.md").open("x") as stream:
        stream.write("\n".join(lines) + "\n")
    with (stage / "report.html").open("x") as stream:
        stream.write('<!doctype html><html lang="en"><meta charset="utf-8"><title>ES Range XV trend lengths</title><body><pre>' + html.escape("\n".join(lines)) + '</pre></body></html>')
    with (stage / "advice.md").open("x") as stream:
        stream.write("# Interpretation\n\nThese are empirical candle-run lengths conditional on complete observed starts and ends. Use their directional and time-window distributions descriptively. Censored runs are separate and can have a different length distribution. No entry rule, directional forecast or trading profitability is established.\n")
    print("Prepared three selected reports; every displayed numeric cell and all four CSV projections per chart verified.")
