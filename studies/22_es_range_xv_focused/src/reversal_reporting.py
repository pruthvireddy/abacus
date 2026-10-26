"""Selected reversal reports from saved CSV strings; no numerical execution."""
from __future__ import annotations

import csv
from datetime import datetime, timezone
import hashlib
import html
import json
from pathlib import Path

LABELS = {"all_hours": "All hours", "asia": "Asia", "london": "London", "ny": "NY",
          "asia_open": "Asia Open", "ny_open": "NY Open", "ny_am": "NY AM", "ny_pm": "NY PM"}
DIRECTIONS = {"bullish": "Bullish reversal", "bearish": "Bearish reversal", "all": "Both directions"}
GROUP = ("year", "timeframe_id", "direction", "prior_leg_bucket")
PRIMARY_RETRACE = ("year", "timeframe_id", "direction", "prior_leg_bucket", "level_percent", "event_count",
                   "valid_f1_count", "unknown_f1_count", "touch_count", "touch_probability",
                   "joint_beyond_close_numerator", "joint_beyond_close_denominator", "joint_beyond_close_probability",
                   "conditional_beyond_close_numerator", "conditional_beyond_close_denominator",
                   "conditional_beyond_close_probability")
FILTERS = [{"key": "year", "label": "Year", "defaultValue": "All years"},
           {"key": "window", "label": "Session / timeframe", "defaultValue": "All hours"},
           {"key": "leg", "label": "Preceding leg"}]
CONTEXT_COLUMNS = [{"key": "year", "label": "Session year"}, {"key": "window", "label": "Window"},
                   {"key": "leg", "label": "Preceding opposite leg"}]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=None if path.name == "publication.json" else 2,
                  separators=(",", ":") if path.name == "publication.json" else None, allow_nan=False)
        stream.write("\n")


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        return list(reader.fieldnames or ()), list(reader)


def number(raw: str) -> int | float | None:
    if raw == "":
        return None
    value = float(raw)
    return int(value) if value.is_integer() else round(value, 6)


def context(source: dict) -> dict:
    bucket = source["prior_leg_bucket"]
    label = ("All preceding legs" if bucket == "all" else "Unknown start" if bucket == "unknown_start"
             else bucket + (" candle" if bucket == "1" else " candles"))
    year = source["year"] or "All years"
    return {"year": year + (" (partial)" if year in ("2019", "2026") else ""),
            "window": LABELS[source["timeframe_id"]], "leg": label}


def build_reports(stage: Path) -> dict:
    run_id = stage.name
    if json.loads((stage / "config.json").read_text())["protocol_version"] != "0.3.0":
        raise ValueError("Reversal report requires frozen protocol 0.3.0")
    paths = {name: stage / "tables" / ("reversal_" + name + ".csv")
             for name in ("summary", "continuation", "retracement")}
    paths["coverage"] = stage / "tables/coverage.csv"
    tables = {name: read_csv(path) for name, path in paths.items()}
    original_hashes = {path.relative_to(stage).as_posix(): sha(path) for path in paths.values()}
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    publications = []
    overall = []
    for setting in (4, 5, 6):
        selected = {name: [(i + 2, row) for i, row in enumerate(rows)
                           if row["setting_ticks"] == str(setting)]
                    for name, (_columns, rows) in tables.items()}
        main = next((i, row) for i, row in selected["summary"] if row["year"] == ""
                    and row["timeframe_id"] == "all_hours" and row["direction"] == "all"
                    and row["prior_leg_bucket"] == "all")
        for view in ("continuation", "retracement"):
            target = stage / "publications" / f"{setting}t-{view}"
            if target.exists():
                raise FileExistsError("Immutable publication source overwrite refused")
            target.mkdir(parents=True)
            bindings = []

            def cell(section, report_row, key, table, line, source_key):
                source = tables[table][1][line - 2]
                value = number(source[source_key])
                bindings.append({"section": section, "report_row": report_row, "column": key,
                                 "source": paths[table].relative_to(stage).as_posix(), "source_row": line,
                                 "source_column": source_key, "original": source[source_key], "value": value})
                return value

            def saved_table(section_id, title, table_name, rows, fields, *, filters=True, description=""):
                result = []
                for line, source in rows:
                    row = context(source) if filters else {"direction": DIRECTIONS[source["direction"]]}
                    for key, original, _label, _format in fields:
                        row[key] = cell(section_id, len(result), key, table_name, line, original)
                    result.append(row)
                columns = CONTEXT_COLUMNS if filters else [{"key": "direction", "label": "Direction"}]
                section = {"id": section_id, "kind": "table", "title": title, "description": description,
                           "columns": [*columns, *[{"key": key, "label": label, "format": form,
                                                     "precision": 2 if form == "percent" else 0}
                                                    for key, _original, label, form in fields]], "rows": result}
                if filters:
                    section["rowFilters"] = FILTERS
                return section

            definition = (
                "R is the first completed non-doji candle directly after a completed opposite-colour candle. "
                "A bullish R follows a bearish leg; a bearish R follows a bullish leg. "
                "n counts additional candles after R: preceding bearish,bearish,bearish → bullish R → bullish F1 → bullish F2 "
                "is a 3-candle preceding leg and a success at n=2. Known preceding lengths use the whole observed leg; "
                "unknown starts have their own group. All preceding legs includes every reversal, including unknown starts. "
                "Choose year, session and preceding leg in the tables. All years + All hours gives overall; a year + All hours "
                "gives yearly; All years + a named window gives session; a year + a window gives year-by-session. "
                "The All preceding legs row overlaps the disjoint size rows; do not sum it with them."
            )
            if view == "continuation":
                definition += (" Continuation requires n uninterrupted completed candles with R's close-open sign. "
                               "An opposite candle or doji is failure. A session/export boundary before classification is unknown. "
                               "Already-observed short-horizon successes remain counted. Rates use each horizon's known success + failure "
                               "population; exact numerator, denominator and unknown counts for every cell are in the four CSVs.")
            else:
                definition += (" F1 is the immediate next completed candle. Retracement is a touch of 25%, 50%, 75% or 100% "
                               "of R's body from its close toward its open; equality counts. A favorable close is strictly beyond R.close "
                               "in R's direction. 100% reaches R.open, rather than the outer wick. Joint rate = touch AND favorable / known F1; "
                               "conditional rate = touch AND favorable / touched F1. These answer different questions. "
                               "OHLC establishes a touch and final close, without resolving the full intrabar path or a tradable fill.")
            sections = [{"id": "definition", "kind": "text", "title": "Read the reversal sequence", "body": definition}]
            items = []
            for key, label in (("event_count", "Observed reversals"), ("covered_sessions", "Covered sessions"),
                               ("eligible_bar_count", "Eligible completed candles"), ("unknown_f1_count", "Unknown F1 outcomes")):
                items.append({"label": label, "value": cell("coverage", len(items), "value", "summary", main[0], key),
                              "format": "number", "precision": 0})
            sections.append({"id": "coverage", "kind": "metrics", "title": "Overall sample", "items": items})
            if view == "continuation":
                for direction in ("bullish", "bearish", "all"):
                    rows = [(i, r) for i, r in selected["continuation"] if r["year"] == "" and r["timeframe_id"] == "all_hours"
                            and r["prior_leg_bucket"] == "all" and r["direction"] == direction]
                    sections.append(saved_table("overall-" + direction, "Overall · " + DIRECTIONS[direction], "continuation", rows,
                                                [("n", "n", "Additional candles n", "number"), ("s", "numerator", "Successes", "number"),
                                                 ("d", "denominator", "Known outcomes", "number"), ("u", "unknown_count", "Unknown", "number"),
                                                 ("p", "probability", "P(at least n)", "percent")], filters=False,
                                                description="R is excluded from n. Denominator = known successes + known failures; unknowns remain separate. No censor-adjusted population estimate is claimed."))
                for direction in ("bullish", "bearish"):
                    for lower, upper in ((1, 8), (9, 16), (17, 20)):
                        section_id = f"n{lower}-{upper}-{direction}"
                        groups = {}
                        for line, row in selected["continuation"]:
                            if row["direction"] != direction or not lower <= int(row["n"]) <= upper:
                                continue
                            key = tuple(row[k] for k in GROUP)
                            if key not in groups:
                                groups[key] = context(row)
                            groups[key]["n" + row["n"]] = cell(section_id, list(groups).index(key), "n" + row["n"], "continuation", line, "probability")
                        sections.append({"id": section_id, "kind": "table", "title": DIRECTIONS[direction] + f" · n={lower}–{upper} by preceding leg",
                                         "description": "Each value is a separately estimated horizon rate. Filter overall, annual, session or annual-by-session cells. Horizon-specific counts and unknowns are supplied in the selected CSVs. 2019/2026 are partial years.",
                                         "rowFilters": FILTERS, "columns": [*CONTEXT_COLUMNS, *[{"key": "n" + str(n), "label": f"n={n}", "format": "percent", "precision": 2} for n in range(lower, upper + 1)]],
                                         "rows": list(groups.values())})
                    sections.append(saved_table("counts-" + direction, DIRECTIONS[direction] + " · sample and unknown outcomes", "summary",
                                                [(i, r) for i, r in selected["summary"] if r["direction"] == direction],
                                                [("e", "event_count", "Reversals", "number"), ("f", "known_f1_count", "Known F1", "number"),
                                                 ("u", "unknown_f1_count", "Unknown F1", "number"), ("c", "censored_followup_count", "Censored full leg", "number"),
                                                 ("s", "sessions_with_events", "Sessions with reversals", "number")],
                                                description="A censored full leg can have known successes at short horizons. Unknown-start prior legs remain a separate size cohort."))
            else:
                rows = [(i, r) for i, r in selected["retracement"] if r["year"] == "" and r["timeframe_id"] == "all_hours" and r["prior_leg_bucket"] == "all"]
                fields = [("l", "level_percent", "Body depth %", "number"), ("f", "valid_f1_count", "Known F1", "number"),
                          ("u", "unknown_f1_count", "Unknown F1", "number"), ("t", "touch_count", "Touched", "number"),
                          ("p", "touch_probability", "P(touch)", "percent"), ("j", "joint_beyond_close_numerator", "Touch + favorable", "number"),
                          ("q", "joint_beyond_close_probability", "Joint %", "percent"),
                          ("r", "conditional_beyond_close_probability", "Favorable given touch %", "percent")]
                description = "Joint % = touch + favorable / known F1. Conditional % = touch + favorable / touched. Unknown F1 is excluded from both denominators; undefined estimates remain blank."
                sections.append(saved_table("overall", "Overall F1 retracement and recovery", "retracement", rows, fields, filters=False, description=description))
                for direction in ("bullish", "bearish"):
                    for level in (25, 50, 75, 100):
                        sections.append(saved_table(f"depth-{level}-{direction}", DIRECTIONS[direction] + f" · {level}% body retracement by preceding leg", "retracement",
                                                    [(i, r) for i, r in selected["retracement"] if r["direction"] == direction and r["level_percent"] == str(level)],
                                                    fields[1:], description=description))
            sections.append({"id": "methods", "kind": "text", "title": "Timing, windows and interpretation",
                             "body": "Event groups use R's completion proxy (when the signal becomes known), rather than its opening or outcome time. Year uses its inferred 18:00-rollover session date. Follow-up continues across named-window endpoints but never across inferred daily sessions or completion barriers. NY wall-time windows: Asia 20:00–02:00; London 02:00–09:00; NY 09:30–16:00; Asia Open 19:30–21:30; NY Open 09:30–10:30; NY AM 10:30–12:30; NY PM 12:30–16:00. Start included, end excluded. Overlapping windows cannot all be summed. 2019 and 2026 have partial coverage. The entire partial final session 2026-09-24 is excluded. Bar coverage is anchored at bar opening, separately from event completion-time groups. Original same-second and identical rows retain source order. OHLC is available; volume, exact completion and contract/roll treatment are unverified. These are descriptive historical frequencies on already-inspected history, without independent forecast validation, iid confidence intervals or trading profitability evidence."})
            downloads = []
            if view == "continuation":
                specs = [(name, original) for name, original in (("probabilities", "probability"), ("successes", "numerator"), ("known-outcomes", "denominator"), ("unknown-outcomes", "unknown_count"))]
                for name, original in specs:
                    projected = {}
                    for line, row in selected["continuation"]:
                        key = tuple(row[k] for k in GROUP)
                        projected.setdefault(key, dict(zip(GROUP, key)))["n" + row["n"]] = row[original]
                    download_rows = list(projected.values())
                    columns = [*GROUP, *["n" + str(n) for n in range(1, 21)]]
                    downloads.append(_download(target, name + ".csv", name.replace("-", " ").title() + " · all preceding legs and horizons", columns, download_rows, paths["continuation"], run_id, view, setting))
                    bindings.append({"download": name + ".csv", "source": paths["continuation"].relative_to(stage).as_posix(),
                                     "source_column": original, "pivot_group": list(GROUP), "pivot_horizon": "n", "setting_ticks": setting,
                                     "sha256": sha(target / "downloads" / (name + ".csv")), "original_strings_verified": True})
            else:
                specs = [("retracement-recovery.csv", "All F1 retracement and recovery outcomes", "retracement", list(PRIMARY_RETRACE)),
                         ("reversal-samples.csv", "Reversal sample, exclusions and prior-leg groups", "summary", [c for c in tables["summary"][0] if c != "setting_ticks"])]
                for filename, label, table_name, columns in specs:
                    rows = [{key: row[key] for key in columns} for _line, row in selected[table_name]]
                    downloads.append(_download(target, filename, label, columns, rows, paths[table_name], run_id, view, setting))
                    bindings.append({"download": filename, "source": paths[table_name].relative_to(stage).as_posix(),
                                     "source_rows": [line for line, _row in selected[table_name]], "columns": columns,
                                     "sha256": sha(target / "downloads" / filename), "original_strings_verified": True})
            name = "Reversal continuation" if view == "continuation" else "Retracement & recovery"
            report = {"schemaVersion": "1.1", "id": f"es-range-xv-reversal-{view}-{setting}t-20261012",
                      "title": f"ES {setting} RXV · {name}", "summary": "Reversal outcomes by preceding leg size, direction, year and all seven session windows. Select a chart, analysis and saved-row filters; exact counts are downloadable.",
                      "publishedAt": timestamp, "source": {"producer": "sahadeva", "runId": run_id}, "sections": sections,
                      "notes": ["Pooled-direction results and exact unrounded counts/rates for every year, window and preceding-leg cohort are included in CSVs. Displayed rates retain six decimals before formatting.",
                                "Continuation uses candle colour; F1 recovery uses its close relative to R.close. A gap can make these outcomes differ."],
                      "downloads": downloads, "references": [{"id": name + "-source", "kind": "saved-artifact", "label": name.title() + " saved evidence", "title": name.title() + " · frozen protocol 0.3.0", "runId": run_id, "artifact": path.relative_to(stage).as_posix(), "sha256": sha(path)} for name, path in paths.items() if name != "coverage"]}
            write_json(target / "publication.json", report)
            actual = json.loads((target / "publication.json").read_text())
            _verify_bindings(actual, bindings, stage, tables, paths)
            write_json(target / "source-map.json", {"schema_version": 1, "run_id": run_id, "source_hashes": original_hashes, "bindings": _compact_bindings(bindings)})
            write_json(target / "verification.json", {"result": "passed", "publication_sha256": sha(target / "publication.json"),
                                                      "numeric_cells_checked": sum("section" in b for b in bindings), "csv_files_checked": len(downloads),
                                                      "original_csv_strings_verified": True})
            publications.append({"path": (target / "publication.json").relative_to(stage).as_posix(), "sha256": sha(target / "publication.json")})
        overall.append({"setting_ticks": setting, "event_count": main[1]["event_count"], "known_f1_count": main[1]["known_f1_count"], "unknown_f1_count": main[1]["unknown_f1_count"]})
    for relative, expected in original_hashes.items():
        if sha(stage / relative) != expected:
            raise ValueError("Saved evidence changed during rendering")
    all_files = [*paths.values(), stage / "input-audit.json", *sorted((stage / "publications").rglob("*"))]
    write_json(stage / "publication-verification.json", {"result": "passed", "run_id": run_id, "publications": publications,
                                                        "artifact_hashes": {p.relative_to(stage).as_posix(): sha(p) for p in all_files if p.is_file()},
                                                        "scope": "All displayed numeric cells and all selected CSV strings compared against saved tables; no numerical execution."})
    lines = ["# ES Range XV reversal continuation and retracement", "", "Protocol 0.3.0. R is the first adjacent opposite completed candle. n excludes R. F1 recovery requires body retracement and a strict close beyond R.close. Preceding-leg groups use exact known starts; unknown starts remain separate.", "", "| RXV | Reversals | Known F1 | Unknown F1 |", "|---|---:|---:|---:|"]
    lines += ["| " + " | ".join(str(row[k]) for k in ("setting_ticks", "event_count", "known_f1_count", "unknown_f1_count")) + " |" for row in overall]
    lines += ["", "All n=1–20 horizons, four F1 depths, prior-leg cohorts, direction/year/window and cross-breakdowns are retained in tables/. Selected publications provide saved-row filters and exact count/rate CSVs. Continuation denominators are horizon-specific. F1 joint and conditional denominators differ. Unknowns are never failures. These historical descriptive rates do not establish forecast validity or profitability."]
    (stage / "report.md").write_text("\n".join(lines) + "\n")
    (stage / "report.html").write_text('<!doctype html><html lang="en"><meta charset="utf-8"><title>ES reversal outcomes</title><body><pre>' + html.escape("\n".join(lines)) + '</pre></body></html>')
    (stage / "advice.md").write_text("# Interpretation\n\nCompare the known historical probabilities using the same preceding-leg, year and window filters. Distinguish the joint frequency of retracement plus recovery from recovery conditional on retracement. Small or unknown cohorts warrant caution. No trading fills, costs or P&L are tested. Frozen definitions and saved counts are the authority.\n")
    return {"result": "passed", "publications": publications}


def _download(target, filename, label, columns, rows, source, run_id, view, setting):
    path = target / "downloads" / filename
    path.parent.mkdir(exist_ok=True)
    with path.open("x", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    header, copied = read_csv(path)
    if header != columns or copied != rows:
        raise ValueError("CSV string projection differs from saved evidence")
    return {"id": filename.removesuffix(".csv"), "path": "downloads/" + filename, "label": label,
            "description": "Exact saved strings, including all 15 preceding-leg cohorts, all directions, overall, yearly, seven windows and year-by-window. Blank estimates are undefined. All cohort overlaps its size cohorts; do not sum them together.",
            "population": "Observed adjacent completed reversals. Unknown future outcomes are separately retained; prior unknown-start legs have their own cohort.",
            "units": "Probabilities are ratios; counts are reversals or sessions as labeled. n is additional candles after R; depth is percent of R body.",
            "scope": f"ES {setting} RXV · {view} · 2019–2026 observed history; final partial session excluded.",
            "mediaType": "text/csv", "sha256": sha(path), "rowCount": len(rows), "columns": columns,
            "source": {"runId": run_id, "artifact": "tables/" + source.name, "sha256": sha(source)}}


def _verify_bindings(report, bindings, stage, tables, paths):
    sections = {section["id"]: section for section in report["sections"]}
    numeric_cells = set()
    for binding in bindings:
        if "section" not in binding:
            continue
        section = sections[binding["section"]]
        value = (section["items"][binding["report_row"]]["value"] if section["kind"] == "metrics"
                 else section["rows"][binding["report_row"]][binding["column"]])
        table_name = next(name for name, path in paths.items() if path.relative_to(stage).as_posix() == binding["source"])
        original = tables[table_name][1][binding["source_row"] - 2][binding["source_column"]]
        if original != binding["original"] or value != number(original) or value != binding["value"]:
            raise ValueError("Displayed numeric cell differs from saved evidence")
        numeric_cells.add((binding["section"], binding["report_row"], binding["column"]))
    for section in report["sections"]:
        if section["kind"] == "metrics":
            for i, _item in enumerate(section["items"]):
                if (section["id"], i, "value") not in numeric_cells:
                    raise ValueError("Metric lacks saved-source binding")
        if section["kind"] == "table":
            for i, row in enumerate(section["rows"]):
                for key, value in row.items():
                    if isinstance(value, (int, float)) or value is None:
                        if (section["id"], i, key) not in numeric_cells:
                            raise ValueError("Numeric cell lacks saved-source binding")
    return len(numeric_cells)


def _compact_bindings(bindings):
    """Retain exact source coordinates without copying large CSV values twice."""
    grouped = {}
    other = []
    for binding in bindings:
        if "section" not in binding:
            other.append(binding)
            continue
        key = (binding["section"], binding["column"], binding["source"], binding["source_column"])
        grouped.setdefault(key, []).append([binding["report_row"], binding["source_row"]])
    return {"numeric_projections": [{"section": section, "column": column, "source": source,
                                      "source_column": source_column, "row_pairs": pairs,
                                      "transform": "blank_to_null_else_numeric_rounded_six_decimals"}
                                     for (section, column, source, source_column), pairs in grouped.items()],
            "downloads": other}
