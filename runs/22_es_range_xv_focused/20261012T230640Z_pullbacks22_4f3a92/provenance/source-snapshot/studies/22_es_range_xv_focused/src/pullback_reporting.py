"""Selected one-candle pullback reports from saved CSV strings; no numerical execution."""
from __future__ import annotations

import csv
from datetime import datetime, timezone
import hashlib
import html
import json
from pathlib import Path

LABELS = {"all_hours": "All hours", "asia": "Asia", "london": "London", "ny": "NY",
          "asia_open": "Asia Open", "ny_open": "NY Open", "ny_am": "NY AM", "ny_pm": "NY PM"}
DIRECTIONS = {"bullish": "Bullish resumption R", "bearish": "Bearish resumption R", "all": "Both directions"}
GROUP = ("year", "timeframe_id", "direction", "earlier_leg_bucket")
PRIMARY_RETRACE = ("year", "timeframe_id", "direction", "earlier_leg_bucket", "level_percent", "event_count",
                   "valid_f1_count", "unknown_f1_count", "touch_count", "touch_probability",
                   "joint_beyond_close_numerator", "joint_beyond_close_denominator", "joint_beyond_close_probability",
                   "conditional_beyond_close_numerator", "conditional_beyond_close_denominator",
                   "conditional_beyond_close_probability")
FILTERS = [{"key": "year", "label": "Year", "defaultValue": "All years"},
           {"key": "window", "label": "Session / timeframe", "defaultValue": "All hours"},
           {"key": "leg", "label": "Earlier trend length"}]
CONTEXT_COLUMNS = [{"key": "year", "label": "Session year"}, {"key": "window", "label": "Window"},
                   {"key": "leg", "label": "Earlier original-direction leg"}]


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
    bucket = source["earlier_leg_bucket"]
    label = ("All earlier legs" if bucket == "all" else "Unknown earlier start" if bucket == "unknown_start"
             else bucket + (" candle" if bucket == "1" else " candles"))
    year = source["year"] or "All years"
    return {"year": year + (" (partial)" if year in ("2019", "2026") else ""),
            "window": LABELS[source["timeframe_id"]], "leg": label}


def build_reports(stage: Path) -> dict:
    run_id = stage.name
    if json.loads((stage / "config.json").read_text())["protocol_version"] != "0.4.0":
        raise ValueError("One-candle pullback report requires frozen protocol 0.4.0")
    paths = {name: stage / "tables" / ("pullback_" + name + ".csv")
             for name in ("summary", "continuation", "retracement", "payoff")}
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
                    and row["earlier_leg_bucket"] == "all")
        for view in ("continuation", "retracement", "payoff"):
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
                                                     "precision": 2 if form == "percent" or key in ("lo", "hi") else 0}
                                                    for key, _original, label, form in fields]], "rows": result}
                if filters:
                    section["rowFilters"] = FILTERS
                return section

            definition = (
                "A is a consecutive original-direction leg, B is exactly one completed opposite-colour candle, "
                "and R is the next completed candle returning to A's direction. All three are adjacent within the same eligible session. "
                "Bullish example: bullish A1,A2,A3 → bearish B → bullish R → bullish F1 → bullish F2. "
                "This has earlier A length 3 and succeeds at n=2; R and B are excluded from n. "
                "Bearish events mirror that sequence. The earlier trend filter measures A, not the one-candle B pullback. "
                "A must have an observed completed end at B. Exact known starts use the whole A length; unknown A starts have their own group. "
                "An A length of one can be simple alternating candles and is not treated as a substantial trend. "
                "Choose year, session and earlier trend length in the tables. All years + All hours gives overall; a year + All hours "
                "gives yearly; All years + a named window gives session; a year + a window gives year-by-session. "
                "The All earlier legs row overlaps the disjoint size rows; do not sum it with them."
            )
            if view == "continuation":
                definition += (" Continuation requires n uninterrupted completed candles with R's close-open sign. "
                               "An opposite candle or doji is failure. A session/export boundary before classification is unknown. "
                               "Already-observed short-horizon successes remain counted. Rates use each horizon's known success + failure "
                               "population; exact numerator, denominator and unknown counts for every cell are in the four CSVs.")
            elif view == "retracement":
                definition += (" F1 is the immediate next completed candle. Retracement is a touch of 25%, 50%, 75% or 100% "
                               "of R's body from its close toward its open; equality counts. A favorable close is strictly beyond R.close "
                               "in R's direction. 100% reaches R.open, rather than the outer wick. Joint rate = touch AND favorable / known F1; "
                               "conditional rate = touch AND favorable / touched F1. These answer different questions. "
                               "OHLC establishes a touch and final close, without resolving the full intrabar path or a tradable fill.")
            else:
                definition += (
                    " The payoff view is a gross OHLC price-path proxy. Reference entry is F1.open after R; "
                    "bullish stop = min(B.low,R.low) − 0.25, bearish stop = max(B.high,R.high) + 0.25. "
                    "Risk is the positive entry-to-stop distance. Separate targets are 1R and 2R. "
                    "Follow ten physical completed candles starting at F1, including opposite/doji candles. "
                    "Each opening is checked before its extrema: an opening beyond a boundary exits at that observed open. "
                    "A sole stop touch gives −1R; a sole target touch gives the target R. Both touched within one candle "
                    "have unresolved order and contribute payoff bounds [−1R,target R]. Otherwise exit at the tenth close. "
                    "A session/completion barrier before resolution is unknown. Missing entry, invalid risk and unresolved outcomes "
                    "are excluded from known-outcome means/rates and listed separately. Win bounds mean strictly positive proxy payoff. "
                    "No fill, costs, slippage, net returns, dollars or portfolio performance are established. "
                    "The nominal 0.25 buffer and exported chart prices do not verify contract or adjustment history."
                )
            sections = [{"id": "definition", "kind": "text", "title": "Read the A → B → R setup", "body": definition}]
            items = []
            for key, label in (("event_count", "Observed A → B → R setups"), ("covered_sessions", "Covered sessions"),
                               ("eligible_bar_count", "Eligible completed candles"), ("unknown_f1_count", "Unknown F1 outcomes")):
                items.append({"label": label, "value": cell("coverage", len(items), "value", "summary", main[0], key),
                              "format": "number", "precision": 0})
            sections.append({"id": "coverage", "kind": "metrics", "title": "Overall sample", "items": items})
            if view == "continuation":
                for direction in ("bullish", "bearish", "all"):
                    rows = [(i, r) for i, r in selected["continuation"] if r["year"] == "" and r["timeframe_id"] == "all_hours"
                            and r["earlier_leg_bucket"] == "all" and r["direction"] == direction]
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
                        sections.append({"id": section_id, "kind": "table", "title": DIRECTIONS[direction] + f" · n={lower}–{upper} by earlier trend length",
                                         "description": "Each value is a separately estimated horizon rate. Filter overall, annual, session or annual-by-session cells. Horizon-specific counts and unknowns are supplied in the selected CSVs. 2019/2026 are partial years.",
                                         "rowFilters": FILTERS, "columns": [*CONTEXT_COLUMNS, *[{"key": "n" + str(n), "label": f"n={n}", "format": "percent", "precision": 2} for n in range(lower, upper + 1)]],
                                         "rows": list(groups.values())})
                    sections.append(saved_table("counts-" + direction, DIRECTIONS[direction] + " · sample and unknown outcomes", "summary",
                                                [(i, r) for i, r in selected["summary"] if r["direction"] == direction],
                                                [("e", "event_count", "Setups", "number"), ("f", "known_f1_count", "Known F1", "number"),
                                                 ("u", "unknown_f1_count", "Unknown F1", "number"), ("c", "censored_followup_count", "Censored full leg", "number"),
                                                 ("s", "sessions_with_events", "Sessions with setups", "number")],
                                                description="A censored full leg can have known successes at short horizons. Unknown-start earlier legs remain a separate size cohort."))
            elif view == "retracement":
                rows = [(i, r) for i, r in selected["retracement"] if r["year"] == "" and r["timeframe_id"] == "all_hours" and r["earlier_leg_bucket"] == "all"]
                fields = [("l", "level_percent", "Body depth %", "number"), ("f", "valid_f1_count", "Known F1", "number"),
                          ("u", "unknown_f1_count", "Unknown F1", "number"), ("t", "touch_count", "Touched", "number"),
                          ("p", "touch_probability", "P(touch)", "percent"), ("j", "joint_beyond_close_numerator", "Touch + favorable", "number"),
                          ("q", "joint_beyond_close_probability", "Joint %", "percent"),
                          ("r", "conditional_beyond_close_probability", "Favorable given touch %", "percent")]
                description = "Joint % = touch + favorable / known F1. Conditional % = touch + favorable / touched. Unknown F1 is excluded from both denominators; undefined estimates remain blank."
                sections.append(saved_table("overall", "Overall F1 retracement and recovery", "retracement", rows, fields, filters=False, description=description))
                for direction in ("bullish", "bearish"):
                    for level in (25, 50, 75, 100):
                        sections.append(saved_table(f"depth-{level}-{direction}", DIRECTIONS[direction] + f" · {level}% body retracement by earlier trend length", "retracement",
                                                    [(i, r) for i, r in selected["retracement"] if r["direction"] == direction and r["level_percent"] == str(level)],
                                                    fields[1:], description=description))
            else:
                fields = [("e", "event_count", "Setups", "number"),
                          ("k", "known_outcome_count", "Known", "number"),
                          ("u", "unknown_outcome_count", "Unknown", "number"),
                          ("i", "invalid_entry_count", "Invalid risk", "number"),
                          ("a", "ambiguous_count", "Order ambiguous", "number"),
                          ("lo", "mean_lower_r", "Gross mean lower R", "number"),
                          ("hi", "mean_upper_r", "Gross mean upper R", "number"),
                          ("wl", "win_rate_lower", "Positive proxy lower %", "percent"),
                          ("wh", "win_rate_upper", "Positive proxy upper %", "percent")]
                description = ("Means and positive-payoff rates use known OHLC proxy outcomes, including bounded intrabar ambiguity. "
                               "Unknown includes missing entry and unresolved path; invalid risk is separate. Bounds reflect order ambiguity, not confidence intervals. "
                               "Overlapping setups and the two target scenarios must not be combined as a trading portfolio.")
                rows = [(i, r) for i, r in selected["payoff"] if r["year"] == "" and r["timeframe_id"] == "all_hours"
                        and r["earlier_leg_bucket"] == "all"]
                sections.append(saved_table("overall-payoff", "Overall gross OHLC payoff bounds", "payoff", rows,
                                            [("t", "target_multiple", "Target R", "number"), *fields],
                                            filters=False, description=description))
                for direction in ("bullish", "bearish", "all"):
                    for target_r in (1, 2):
                        rows = [(i, r) for i, r in selected["payoff"] if r["direction"] == direction
                                and r["target_multiple"] == str(target_r)]
                        sections.append(saved_table(f"target-{target_r}r-{direction}",
                                                    DIRECTIONS[direction] + f" · {target_r}R target by earlier trend length", "payoff", rows,
                                                    fields, description=description))
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
                    downloads.append(_download(target, name + ".csv", name.replace("-", " ").title() + " · all earlier legs and horizons", columns, download_rows, paths["continuation"], run_id, view, setting))
                    bindings.append({"download": name + ".csv", "source": paths["continuation"].relative_to(stage).as_posix(),
                                     "source_column": original, "pivot_group": list(GROUP), "pivot_horizon": "n", "setting_ticks": setting,
                                     "sha256": sha(target / "downloads" / (name + ".csv")), "original_strings_verified": True})
            elif view == "retracement":
                specs = [("retracement-recovery.csv", "All F1 retracement and recovery outcomes", "retracement", list(PRIMARY_RETRACE)),
                         ("setup-samples.csv", "Setup sample, exclusions and earlier-leg groups", "summary", [c for c in tables["summary"][0] if c != "setting_ticks"])]
                for filename, label, table_name, columns in specs:
                    rows = [{key: row[key] for key in columns} for _line, row in selected[table_name]]
                    downloads.append(_download(target, filename, label, columns, rows, paths[table_name], run_id, view, setting))
                    bindings.append({"download": filename, "source": paths[table_name].relative_to(stage).as_posix(),
                                     "source_rows": [line for line, _row in selected[table_name]], "columns": columns,
                                     "sha256": sha(target / "downloads" / filename), "original_strings_verified": True})
            else:
                columns = [*GROUP, "target_multiple", "horizon_candles", "event_count", "valid_entry_count",
                           "invalid_entry_count", "unknown_entry_count", "known_outcome_count", "unknown_outcome_count",
                           "resolved_count", "ambiguous_count", "marked_count", "win_lower_numerator", "win_upper_numerator",
                           "denominator", "win_rate_lower", "win_rate_upper", "mean_lower_r", "mean_upper_r",
                           "sessions_with_events", "sessions_with_known_outcome"]
                resolution = [*GROUP, "target_multiple", "horizon_candles", "event_count", "valid_entry_count",
                              "invalid_entry_count", "unknown_entry_count", "known_outcome_count", "unknown_outcome_count",
                              "resolved_count", "ambiguous_count", "marked_count", "target_touch_count", "stop_touch_count",
                              "gap_target_count", "gap_stop_count", "payoff_lower_sum_r", "payoff_upper_sum_r",
                              "sessions_with_events", "sessions_with_valid_entry", "sessions_with_known_outcome"]
                for filename, label, projection in (("gross-ohlc-payoff.csv", "Gross OHLC payoff proxy · exact counts and bounds", columns),
                                                    ("payoff-resolution.csv", "OHLC scenario resolution · touch, gap and horizon outcomes", resolution)):
                    if len(projection) > 24:
                        raise ValueError("Explicit selected payoff columns exceed Narada bound")
                    rows = [{key: row[key] for key in projection} for _line, row in selected["payoff"]]
                    downloads.append(_download(target, filename, label, projection, rows, paths["payoff"], run_id, view, setting))
                    bindings.append({"download": filename, "source": paths["payoff"].relative_to(stage).as_posix(),
                                     "source_rows": [line for line, _row in selected["payoff"]], "columns": projection,
                                     "sha256": sha(target / "downloads" / filename), "original_strings_verified": True})
            name = {"continuation": "One-candle pullback continuation", "retracement": "One-candle pullback retracement",
                    "payoff": "Gross OHLC payoff proxy"}[view]
            report = {"schemaVersion": "1.1", "id": f"es-range-xv-pullback-{view}-{setting}t-20261012",
                      "title": f"ES {setting} RXV · {name}", "summary": "Earlier trend → one opposite candle → resumption. Compare saved results by earlier trend length, direction, year and all seven session windows; exact counts are downloadable.",
                      "publishedAt": timestamp, "source": {"producer": "sahadeva", "runId": run_id}, "sections": sections,
                      "notes": ["Pooled-direction results and exact unrounded counts/rates for every year, window and earlier-leg cohort are included in CSVs. Displayed rates retain six decimals before formatting.",
                                ("Payoff bounds are gross OHLC scenarios in entry-to-stop R units. Costs and executable fills are unmodeled; no net profitability claim."
                                 if view == "payoff" else "Continuation uses candle colour; F1 recovery uses its close relative to R.close. A gap can make these outcomes differ.")],
                      "downloads": downloads, "references": [{"id": name + "-source", "kind": "saved-artifact", "label": name.title() + " saved evidence", "title": name.title() + " · frozen protocol 0.4.0", "runId": run_id, "artifact": path.relative_to(stage).as_posix(), "sha256": sha(path)} for name, path in paths.items() if name != "coverage"]}
            write_json(target / "publication.json", report)
            actual = json.loads((target / "publication.json").read_text())
            _verify_bindings(actual, bindings, stage, tables, paths)
            write_json(target / "source-map.json", {"schema_version": 1, "run_id": run_id, "source_hashes": original_hashes,
                       "context_projection": {"year": "saved year or All years, partial marker for 2019/2026",
                                              "window": "saved timeframe_id via declared NY-window labels",
                                              "leg": "saved earlier_leg_bucket, not the one-candle B length",
                                              "direction": "saved direction, with pooled all label"},
                       "bindings": _compact_bindings(bindings)})
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
    lines = ["# ES Range XV one-candle pullback continuation and retracement", "", "Protocol 0.4.0. A is an original-direction leg, B is exactly one opposite candle, R resumes A direction. n excludes R. F1 recovery requires body retracement and a strict close beyond R.close. Earlier A-leg groups use exact known starts; unknown starts remain separate.", "", "| RXV | Setups | Known F1 | Unknown F1 |", "|---|---:|---:|---:|"]
    lines += ["| " + " | ".join(str(row[k]) for k in ("setting_ticks", "event_count", "known_f1_count", "unknown_f1_count")) + " |" for row in overall]
    lines += ["", "Gross OHLC payoff proxy: F1.open reference, adverse B/R extreme plus a nominal 0.25 stop buffer, 1R/2R targets, ten physical candles. Both-extrema order has explicit payoff bounds; no net or executable profitability estimate.", "", "All n=1–20 horizons, four F1 depths, earlier-leg cohorts, direction/year/window and cross-breakdowns are retained in tables/. Selected publications provide saved-row filters and exact count/rate CSVs. Continuation denominators are horizon-specific. F1 joint and conditional denominators differ. Unknowns are never failures. These historical descriptive rates do not establish forecast validity or profitability."]
    (stage / "report.md").write_text("\n".join(lines) + "\n")
    (stage / "report.html").write_text('<!doctype html><html lang="en"><meta charset="utf-8"><title>ES one-candle pullback outcomes</title><body><pre>' + html.escape("\n".join(lines)) + '</pre></body></html>')
    (stage / "advice.md").write_text("# Interpretation\n\nCompare the known historical probabilities using the same earlier-leg, year and window filters. Distinguish the joint frequency of retracement plus recovery from recovery conditional on retracement. Small or unknown cohorts warrant caution. Gross OHLC payoff bounds are reference-price scenarios only, with unresolved intrabar order retained. No trading fills, costs or net P&L are tested. Frozen definitions and saved counts are the authority.\n")
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
            "description": "Exact saved strings, including all 15 earlier-leg cohorts, all directions, overall, yearly, seven windows and year-by-window. Blank estimates are undefined. All cohort overlaps its size cohorts; do not sum them together.",
            "population": "Observed completed A → single opposite B → same-direction R setups. Unknown future outcomes are separately retained; earlier unknown-start legs have their own cohort.",
            "units": ("Gross price-path payoff in R = entry-to-stop distance. Ratios are positive-payoff bounds on known scenarios; counts retain missing/invalid/unknown/ambiguous outcomes. No costs or executable fills."
                      if view == "payoff" else "Probabilities are ratios; counts are setups or sessions as labeled. n is additional candles after R; depth is percent of R body."),
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
        if section["kind"] == "table":
            report_row = section["rows"][binding["report_row"]]
            source_row = tables[table_name][1][binding["source_row"] - 2]
            expected_context = context(source_row) if "rowFilters" in section else {"direction": DIRECTIONS[source_row["direction"]]}
            if any(report_row.get(key) != expected for key, expected in expected_context.items()):
                raise ValueError("Displayed cohort context differs from saved evidence")
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
