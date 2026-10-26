"""Independent saved-cell publication transfer check; never imports producers.

This verifies explicitly selected source bytes/cells, claim conditions, downloads
and example traces. Scientific reconciliation and actual browser review have
separate receipts. Raster rendering needs the recorded visual review as well as
the exact saved figure-data identities checked here.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import shutil
import sys
from collections import Counter
import xml.etree.ElementTree as ET
from typing import Any


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def safe_file(stage: Path, relative: str) -> Path:
    path = PurePosixPath(relative)
    require(not path.is_absolute() and relative and all(x not in {"", ".", ".."} for x in path.parts), "unsafe artifact path")
    require(str(path) == relative, "noncanonical artifact path")
    require("\\" not in relative, "unsafe artifact separator")
    target = stage.joinpath(*path.parts)
    require(target.is_file() and not target.is_symlink(), f"ordinary artifact required: {relative}")
    for ancestor in target.parents:
        if ancestor == stage:
            break
        require(not ancestor.is_symlink(), "symlinked artifact ancestor")
    return target


def load_json(path: Path) -> Any:
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, f"duplicate JSON key: {key}")
            result[key] = value
        return result
    with path.open() as stream:
        return json.load(stream, object_pairs_hook=unique,
                         parse_constant=lambda x: (_ for _ in ()).throw(ValueError("nonfinite JSON number")))


def csv_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream, strict=True)
        headers = reader.fieldnames or []
        require(headers and len(headers) == len(set(headers)), "unique CSV headers required")
        rows = list(reader)
    require(all(None not in row and all(value is not None for value in row.values()) for row in rows), "malformed CSV width")
    return headers, rows


def typed(value: str, value_type: str) -> Any:
    if value_type in {"string", "text"}:
        return value
    if value_type == "null":
        require(value == "", "declared null source must be blank")
        return None
    if value == "":
        return None
    if value_type in {"boolean", "bool"}:
        require(value in {"True", "False", "true", "false"}, "invalid source boolean")
        return value.lower() == "true"
    require(value_type in {"number", "integer", "int", "float"}, "unknown source value type")
    result = float(value)
    require(math.isfinite(result), "nonfinite saved numeric cell")
    if value_type in {"integer", "int"}:
        require(result.is_integer(), "source integer not integral")
        return int(result)
    return result


def same(actual: Any, expected: Any, context: str) -> None:
    if expected is None or isinstance(expected, (str, bool)):
        require(type(actual) is type(expected) and actual == expected, f"cell transfer mismatch: {context}")
    else:
        require(type(actual) in {int, float} and math.isfinite(actual), f"numeric type mismatch: {context}")
        require(math.isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-9), f"numeric transfer mismatch: {context}")


class SavedCells:
    def __init__(self, stage: Path, records: list[dict[str, Any]]):
        self.stage, self.tables, self.pins = stage, {}, {}
        for item in records:
            path = item.get("path", item.get("source_artifact"))
            require(path not in self.pins, "duplicate source artifact pin")
            file = safe_file(stage, path)
            require(digest(file) == item["sha256"], f"source artifact bytes changed: {path}")
            self.pins[path] = item["sha256"]

    def table(self, path: str) -> tuple[list[str], list[dict[str, str]]]:
        require(path in self.pins, f"unbound source artifact: {path}")
        if path not in self.tables:
            self.tables[path] = csv_rows(safe_file(self.stage, path))
        return self.tables[path]

    def cell(self, binding: dict[str, Any]) -> Any:
        path = binding["source_artifact"]
        if "source_pointer" in binding:
            require(path in self.pins, "unbound JSON source artifact")
            pointer = binding["source_pointer"]
            require(pointer.startswith("/"), "explicit JSON pointer required")
            value = load_json(safe_file(self.stage, path))
            for token in pointer[1:].split("/"):
                token = token.replace("~1", "/").replace("~0", "~")
                value = value[int(token)] if isinstance(value, list) else value[token]
            inferred = "string" if type(value) is str else "boolean" if type(value) is bool else "number"
            kind = binding.get("value_type", inferred)
            if value is None:
                return None
            if kind in {"number", "float", "integer", "int"}:
                require(type(value) in {int, float} and math.isfinite(value), "JSON source numeric type mismatch")
                if kind in {"integer", "int"}:
                    require(float(value).is_integer(), "JSON source integer not integral")
                    return int(value)
            elif kind in {"boolean", "bool"}:
                require(type(value) is bool, "JSON source boolean type mismatch")
            elif kind in {"string", "text"}:
                require(type(value) is str, "JSON source string type mismatch")
            else:
                raise ValueError("unknown JSON source type")
            return value
        _, rows = self.table(path)
        row_number = binding["source_row"]
        require(type(row_number) is int and 0 <= row_number < len(rows), "invalid zero-based original source row")
        column = binding["source_column"]
        require(column in rows[row_number], f"source column absent: {column}")
        return typed(rows[row_number][column], binding.get("value_type", "number"))


def verify_cells(report: dict[str, Any], source_map: dict[str, Any], saved: SavedCells) -> int:
    expected: dict[tuple[Any, ...], Any] = {}
    for section in report["sections"]:
        if section["kind"] == "table":
            for index, row in enumerate(section["rows"]):
                for key, value in row.items():
                    expected[(section["id"], "row", index, key)] = value
        if section["kind"] == "metrics":
            for index, item in enumerate(section["items"]):
                expected[(section["id"], "metric", index)] = item["value"]
    observed = set()
    bindings = source_map.get("bindings", []) + source_map.get("metric_bindings", [])
    for binding in bindings:
        section = binding.get("section", binding.get("section_id"))
        if "metric_index" in binding:
            key = (section, "metric", binding["metric_index"])
        else:
            key = (section, "row", binding["row_index"], binding["key"])
        require(key in expected, f"binding target not displayed: {key}")
        require(key not in observed, f"duplicate display binding: {key}")
        same(expected[key], saved.cell(binding), str(key))
        observed.add(key)
    require(observed == set(expected), f"unbound displayed cells: {len(set(expected)-observed)}")
    return len(observed)


def verify_downloads(stage: Path, report: dict[str, Any], source_map: dict[str, Any], saved: SavedCells) -> int:
    maps = {item["id"]: item for item in source_map.get("downloads", [])}
    require(len(maps) == len(source_map.get("downloads", [])), "duplicate download map")
    count = 0
    for declaration in report.get("downloads", []):
        require(declaration["id"] in maps, "download without source map")
        mapping = maps.pop(declaration["id"])
        target = safe_file(stage, declaration["path"])
        require(digest(target) == declaration["sha256"], "selected download bytes changed")
        source = declaration["source"]
        require(source["runId"] == report["source"]["runId"], "download run mismatch")
        require(source["artifact"] in saved.pins and source["sha256"] == saved.pins[source["artifact"]], "download source pin mismatch")
        columns, selected = csv_rows(target)
        require(columns == declaration["columns"] and len(selected) == declaration["rowCount"], "download header/count mismatch")
        source_headers, rows = saved.table(source["artifact"])
        require(all(column in source_headers for column in columns), "invented download column")
        require(mapping["source_artifact"] == source["artifact"] and mapping["columns"] == columns, "download mapping attribution mismatch")
        indices = mapping["source_rows"]
        require(len(indices) == len(selected) and indices == sorted(set(indices)), "download original row ordering/cardinality mismatch")
        for output, original in zip(selected, indices):
            require(type(original) is int and 0 <= original < len(rows), "download source row invalid")
            require(output == {key: rows[original][key] for key in columns}, "download changed original CSV strings")
            count += len(columns)
    require(not maps, "source map contains undeclared download")
    return count


def verify_claims(report: dict[str, Any], source_map: dict[str, Any], saved: SavedCells) -> int:
    sections = {section["id"]: section for section in report["sections"]}
    count = 0
    for claim in source_map.get("claims", []):
        target = claim.get("target", {})
        section = target.get("section", claim.get("section"))
        field = target.get("field", "body")
        text = report.get(field) if section is None else sections[section].get(field)
        require(isinstance(text, str) and claim["text"] in text, "claim text no longer displayed")
        if claim.get("rule") == "negative_annual_years":
            require(claim.get("sources"), "negative annual claim lacks full annual evidence")
            annual = []
            for source in claim["sources"]:
                if source.get("source_artifact") != "tables/cohorts.csv" or source.get("source_column") != "net_dollars":
                    continue
                _, table = saved.table(source["source_artifact"])
                row = table[source["source_row"]]
                require(row["year"] != "all" and row["session"] == "all" and row["side"] == "combined", "negative annual claim includes wrong cohort")
                annual.append(row)
            require({row["year"] for row in annual} == {str(y) for y in range(2018,2027)}, "negative annual claim omits covered year")
            losing = [row["year"] for row in annual if row["net_dollars"] != "" and float(row["net_dollars"]) < 0]
            sentence = "Negative annual net P&L occurs in " + ", ".join(losing) + "."
            require(sentence in claim["text"], "negative annual prose list does not match all saved years")
            count += len(annual)
        for source in claim.get("sources", []):
            if "source_column" not in source and "source_pointer" not in source:
                continue
            value = saved.cell(source)
            if "display" in source:
                display = source["display"]
                style = display["style"]
                if style == "verbatim":
                    require(type(value) is str and value in claim["text"], "prose printed string source differs")
                    count += 1
                    continue
                precision = display.get("precision", 0)
                require(type(value) in {int, float} and type(precision) is int, "claim formatted source not numeric")
                numeric = value * 100 if style == "percent" else value
                token = format(numeric, f'{"," if display.get("grouping", True) else ""}.{precision}f')
                token = "$" + token if style == "dollars" else token + "%" if style == "percent" else token
                require(token in claim["text"], "prose printed source value differs")
                count += 1
            elif claim.get("id") == "input-coverage":
                token = value if type(value) is str else f"{value:,.0f}" if type(value) in {int, float} and float(value).is_integer() else None
                require(token is not None and token in claim["text"], "input coverage prose differs from pinned source")
                count += 1
        for condition in claim.get("conditions", []):
            left = saved.cell(condition)
            right = saved.cell(condition["other_cell"]) if "other_cell" in condition else condition.get("value")
            if "other_cell" in condition and "right_factor" in condition:
                right *= condition["right_factor"]
            op = condition["operator"]
            require(op in {"gt", "ge", "lt", "le", "eq", "ne", "nonnull", "null"}, "unsupported claim rule")
            if op in {"gt", "ge", "lt", "le"}:
                require(type(left) in {int, float} and type(right) in {int, float}, "claim requires defined numeric cells")
            good = ((left is not None) if op == "nonnull" else (left is None) if op == "null" else
                    left > right if op == "gt" else left >= right if op == "ge" else
                    left < right if op == "lt" else left <= right if op == "le" else
                    left == right if op == "eq" else left != right)
            require(good, f"prose claim condition false: {claim.get('id')}")
            count += 1
    return count


def verify_svg(stage: Path, section: dict[str, Any], provenance: dict[str, Any], saved: SavedCells) -> int:
    """Check saved raster-source geometry/labels against independent saved rows."""
    svg_relative = provenance.get("svg_path", str(PurePosixPath(section["path"]).with_suffix(".svg")))
    svg_file = safe_file(stage, svg_relative)
    if "svg_sha256" in provenance:
        require(digest(svg_file) == provenance["svg_sha256"], "figure SVG source bytes changed")
    tree = ET.parse(svg_file).getroot()
    texts = ["".join(element.itertext()) for element in tree.iter() if element.tag.endswith("}text")]
    if provenance["kind"] == "illustrative":
        combined = " ".join(texts).lower()
        require("illustrative" in combined and "midpoint" in combined and "never traded" in combined, "SVG illustration trade-scope label missing")
        return 0
    _, all_rows = saved.table(provenance["source_artifact"])
    selected = [all_rows[i] for i in provenance["source_rows"]]
    sid = section["id"]
    plots = [element for element in tree.iter() if element.tag.endswith("}polyline")]
    def instant(raw):
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).timestamp()
    def scaled(values, top, bottom):
        low, high = min([0, *values]), max([0, *values])
        padding = (high-low or 1) * .08
        low, high = low-padding, high+padding
        return lambda value: bottom - (value-low) / (high-low) * (bottom-top)
    def coordinates(element):
        return [tuple(map(float, pair.split(","))) for pair in element.attrib["points"].split()]
    def close_geometry(actual, expected):
        require(len(actual) == len(expected), "figure geometry point count changed")
        for observed, value in zip(actual, expected):
            require(len(observed) == len(value) and all(abs(a-b) <= .011 for a,b in zip(observed, value)), "figure geometry does not match saved evidence")
    if sid == "equity-path":
        require(len(plots) == 2, "equity/drawdown curve count mismatch")
        ts = [instant(row["exit_time"]) for row in selected]
        xmin, xmax = min(ts), max(ts)
        xs = lambda value: 110 + (value-xmin)/(xmax-xmin or 1)*1050
        for plot, field, top, bottom in zip(plots, ["cumulative_net_dollars", "drawdown_dollars"], [130, 515], [420, 750]):
            values = [float(row[field]) for row in selected]
            ys = scaled(values, top, bottom)
            close_geometry(coordinates(plot), [(xs(t),ys(v)) for t,v in zip(ts,values)])
        return 2 * len(selected)
    if sid in {"annual-chart", "session-chart", "hour-chart", "side-chart"}:
        field = "executable_fills" if sid in {"session-chart", "hour-chart"} else "net_dollars"
        values = [None if row[field] == "" else float(row[field]) for row in selected]
        ys = scaled([v for v in values if v is not None], 135, 525)
        rectangles = [element for element in tree.iter() if element.tag.endswith("}rect") and "x" in element.attrib]
        require(len(rectangles) == sum(v is not None for v in values), "saved bar/rectangle count mismatch")
        gap, j = 1050 / len(values), 0
        labels = Counter(texts)
        for i, value in enumerate(values):
            if value is None:
                continue
            x = 110 + gap * (i+.5)
            actual = [float(rectangles[j].attrib[key]) for key in ["x", "y", "width", "height"]]
            expect = [x-gap*.3, min(ys(0), ys(value)), gap*.6, max(abs(ys(value)-ys(0)),1)]
            close_geometry([actual], [expect])
            token = str(int(value)) if field == "executable_fills" else f"${value:,.0f}"
            require(labels[token] > 0, "saved chart value label absent or changed")
            labels[token] -= 1
            j += 1
        return j
    if sid == "year-session-chart":
        positioned = {(round(float(e.attrib["x"]), 2), round(float(e.attrib["y"]), 2)): "".join(e.itertext())
            for e in tree.iter() if e.tag.endswith("}text")}
        sessions = ["Asia", "London", "New York", "Outside"]
        for row in selected:
            i, j = int(row["year"])-2018, sessions.index(row["session"])
            token = "— / zero support" if row["net_dollars"] == "" else f'${float(row["net_dollars"]):,.0f}'
            require(positioned[(297+j*205,160+i*62)] == token, "heatmap cell differs from saved source row")
        return len(selected)
    # Empirical panel geometry is checked with separately verified pinned bars.
    if provenance["source_artifact"] == "tables/selected-example-bars.csv":
        selections = load_json(safe_file(stage, "example-selection.json"))
        require(len(plots) == len(selections), "empirical curve/panel count mismatch")
        for panel, (plot, selection) in enumerate(zip(plots, selections)):
            trade = selection["trade"]
            observed = [row for row in selected if row["trade_id"] == trade["trade_id"]]
            left, right = 85 + (panel%2)*690, 685 + (panel%2)*690
            top, bottom = 180 + (panel//2)*450, 450 + (panel//2)*450
            ts = [instant(row["timestamp"]) for row in observed]
            xs = lambda t: left+(t-min(ts))/(max(ts)-min(ts) or 1)*(right-left)
            values = [float(row[key]) for row in observed for key in ("high", "low")]
            values += [v for v in [trade["initial_stop"],trade["reset_stop"]] if v is not None]
            low, high = min(values), max(values)
            pad = (high-low or 1)*.08
            low, high = low-pad, high+pad
            ys = lambda p: bottom-(p-low)/(high-low)*(bottom-top)
            close_geometry(coordinates(plot), [(xs(t),ys(float(row["close"]))) for t,row in zip(ts,observed)])
            require(trade["contract"] in texts and trade["broker_day"] in " ".join(texts), "empirical contract/date annotation absent")
        return len(selected)
    raise ValueError(f"unreviewed saved-result SVG layout: {sid}")


def verify_references(stage: Path, report: dict[str, Any], saved: SavedCells) -> int:
    count = 0
    geometry_cells = 0
    for reference in report.get("references", []):
        if reference["kind"] == "saved-artifact":
            require(reference["runId"] == report["source"]["runId"], "reference run mismatch")
            artifact = reference["artifact"]
            require(artifact in saved.pins and digest(safe_file(stage, artifact)) == reference["sha256"] == saved.pins[artifact], "saved reference bytes mismatch")
            count += 1
    return count


def verify_examples(stage: Path) -> dict[str, int]:
    """Trace authored examples independently to saved fills and pinned minute bytes."""
    import pandas as pd
    import pyarrow.parquet as pq
    selections = load_json(safe_file(stage, "example-selection.json"))
    _, trade_rows = csv_rows(safe_file(stage, "tables/primary-trades.csv"))
    trades = {row["trade_id"]: row for row in trade_rows}
    _, example_rows = csv_rows(safe_file(stage, "tables/selected-example-bars.csv"))
    audit_inventory = load_json(safe_file(stage, "input-audit/audit-artifacts.json"))
    minute_pin = next(item for item in audit_inventory if item["path"] == "minutes.parquet")
    minute_path = safe_file(stage, "input-audit/minutes.parquet")
    require(digest(minute_path) == minute_pin["sha256"], "pinned minute audit bytes changed")
    selected_ids = set()
    require(len(selections) == 4, "expected earliest winning/losing example for both sides")
    total = 0
    for selection in selections:
        side, outcome = selection["side"], selection["outcome"]
        candidates = [row for row in trade_rows if row["side"] == side and row["status"] == "completed" and
                      (float(row["net_dollars"]) > 1e-8 if outcome == "win" else float(row["net_dollars"]) < -1e-8)]
        expected = min(candidates, key=lambda row: row["entry_time"])
        require(selection["trade_id"] == expected["trade_id"], "empirical example is not prescribed earliest outcome")
        require(selection["rule"] == "earliest chronological completed net win/loss per side", "selection rule changed")
        for key, value in selection["trade"].items():
            require(key in expected, "example ledger field not saved")
            value_type = "null" if value is None else "boolean" if type(value) is bool else "number" if type(value) in {int, float} else "string"
            same(value, typed(expected[key], value_type), f"example ledger {key}")
        selected_ids.add(selection["trade_id"])
        selected = [row for row in example_rows if row["trade_id"] == selection["trade_id"]]
        require(selected and all(row["contract"] == expected["contract"] for row in selected), "example crosses contract or has no bars")
        start = pd.Timestamp(expected["broker_day"] + "T00:00:00+03:00").tz_convert("UTC")
        end = pd.Timestamp(expected["exit_time"]) + pd.Timedelta(minutes=1)
        source = pq.read_table(minute_path, columns=["timestamp", "open", "high", "low", "close", "contract"],
            filters=[("timestamp", ">=", start.to_pydatetime()), ("timestamp", "<", end.to_pydatetime()), ("contract", "=", expected["contract"])]).to_pandas()
        require(len(source) == len(selected), "example source minute scope/cardinality mismatch")
        for row, original in zip(selected, source.itertuples(index=False)):
            require(pd.Timestamp(row["timestamp"]) == original.timestamp, "example minute time mismatch")
            require(row["contract"] == original.contract, "example contract mismatch")
            for key in ("open", "high", "low", "close"):
                same(float(row[key]), float(getattr(original, key)), f"example minute {key}")
                total += 1
    require({row["trade_id"] for row in example_rows} == selected_ids, "unselected example bars included")
    return {"examples": len(selections), "example_minute_price_cells": total}


def assess(stage: Path) -> dict[str, Any]:
    initial = {name: digest(safe_file(stage, name)) for name in ["publication.json", "source-map.json"]}
    report = load_json(safe_file(stage, "publication.json"))
    mapping = load_json(safe_file(stage, "source-map.json"))
    require(report["source"]["runId"] == stage.name == mapping["run_id"], "publication run identity mismatch")
    require(mapping["source_row_base"] == 0, "explicit zero-based source row convention required")
    saved = SavedCells(stage, mapping["source_artifacts"])
    initial.update(saved.pins)
    for declaration in report.get("downloads", []):
        initial[declaration["path"]] = declaration["sha256"]
    displayed = verify_cells(report, mapping, saved)
    download = verify_downloads(stage, report, mapping, saved)
    claims = verify_claims(report, mapping, saved)
    references = verify_references(stage, report, saved)
    figures = {item["path"]: item for item in mapping.get("figures", [])}
    count = 0
    for section in report["sections"]:
        if section["kind"] != "figure":
            continue
        require(section["path"] in figures, "figure lacks source provenance")
        provenance = figures[section["path"]]
        require(digest(safe_file(stage, section["path"])) == provenance["image_sha256"], "figure bytes changed")
        initial[section["path"]] = provenance["image_sha256"]
        svg_path = provenance.get("svg_path", str(PurePosixPath(section["path"]).with_suffix(".svg")))
        require("svg_sha256" in provenance, "retained SVG source pin required")
        initial[svg_path] = provenance["svg_sha256"]
        require(provenance.get("kind") in {"illustrative", "saved-values"}, "figure role unspecified")
        source_path = provenance["source_artifact"]
        require(source_path in saved.pins and provenance["sha256"] == saved.pins[source_path], "figure source bytes not pinned")
        if provenance["kind"] == "illustrative":
            combined = (section.get("caption", "") + " " + section["alt"]).lower()
            require("illustrative" in combined and "midpoint" in combined and ("not traded" in combined or "never traded" in combined), "illustrative midpoint not clearly excluded from trades")
        else:
            _, source_rows = saved.table(source_path)
            indices = provenance["source_rows"]
            columns = provenance["source_columns"]
            plotted = provenance["plotted_values"]
            require(len(plotted) == len(indices), "figure plotted/source cardinality mismatch")
            for point, original in zip(plotted, indices):
                require(point["source_row"] == original and 0 <= original < len(source_rows), "figure original source row mismatch")
                require(set(point["values"]) == set(columns), "figure plotted column coverage mismatch")
                for column, actual in point["values"].items():
                    raw = source_rows[original][column]
                    value_type = "null" if actual is None else "boolean" if type(actual) is bool else "number" if type(actual) in {int, float} else "string"
                    same(actual, typed(raw, value_type), f"figure plotted {original}:{column}")
        count += 1
        geometry_cells += verify_svg(stage, section, provenance, saved)
    examples = verify_examples(stage)
    visual_path = "verification/publication-visual-review-final.json"
    visual = load_json(safe_file(stage, visual_path))
    require(visual["result"] == "passed" and visual["run_id"] == stage.name, "actual final image/prose review required")
    visual_figures = {row["path"]: row["sha256"] for row in visual["figures"]}
    require(set(visual_figures) == {section["path"] for section in report["sections"] if section["kind"] == "figure"}, "actual image review coverage differs")
    for path, pin in visual_figures.items():
        require(digest(safe_file(stage, path)) == pin, "actual reviewed raster differs")
    require(visual["publication_sha256"] == initial["publication.json"], "actual reviewed prose differs")
    initial[visual_path] = digest(safe_file(stage, visual_path))
    checked = {name: digest(safe_file(stage, name)) for name in initial}
    require(checked == initial, "publication/source/asset bytes changed during verification")
    return {"result": "passed", "study_id": "23_gc_overnight_breakout_15m", "run_id": stage.name,
        "publication_id": report["id"], "displayed_cells": displayed, "download_cells": download,
        "claim_conditions": claims, "saved_references": references, "figures": count,
        "figure_geometry_source_observations": geometry_cells, **examples,
        "artifact_hashes": checked, "source_row_base": 0, "numeric_tolerance": {"relative": 1e-12, "absolute": 1e-9},
        "scope": "Independent source-byte, every displayed table/metric cell, typed string/boolean/null preservation, all selected CSV cells, declared prose rule conditions, references, figure identity/source pins and empirical earliest-example pinned-minute trace; no publisher or research producer imports.",
        "visual_review": visual_path,
        "limitations": ["Raster image/prose review is recorded separately and bound to this receipt; automated SVG geometry and saved-cell checks do not prove browser layout.", "This check does not repeat statistical research or native TradingView execution.", "Browser behavior and hosted bytes have independent gates."]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", type=Path, required=True)
    args = parser.parse_args()
    stage = args.stage.resolve()
    here = Path(__file__).resolve()
    snapshot = stage / "verification" / "verify_publication.py"
    snapshot.parent.mkdir(parents=True, exist_ok=True)
    if snapshot.exists():
        require(digest(snapshot) == digest(here), "retained publication checker differs; preserve prior check")
    else:
        shutil.copyfile(here, snapshot)
    receipt = assess(stage)
    require(digest(snapshot) == digest(here), "checker changed during verification")
    receipt.update({"checker_source": {"path": str(snapshot.relative_to(stage)), "sha256": digest(snapshot)},
        "command": {"argv": [sys.executable, *sys.argv], "cwd": str(Path.cwd())}, "python": sys.version,
        "verified_at": datetime.now(timezone.utc).isoformat()})
    target = stage / "publication-verification.json"
    with target.open("x") as stream:
        json.dump(receipt, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({key: receipt[key] for key in ("result", "displayed_cells", "download_cells", "claim_conditions", "figures", "examples")}))


if __name__ == "__main__":
    main()
