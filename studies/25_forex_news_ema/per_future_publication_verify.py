#!/usr/bin/env python3
"""Independent audit of selected publication cells and original-source preservation.

No author verification or numerical-production function is imported or called.
Checks source-to-report transfer and hashes; it does not certify chart pixels,
economic interpretation, original price reconstruction or native TradingView runs.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import struct
import sys

SYMBOLS = ("6E", "6B", "6J", "6A", "6C", "6S")
FAMILIES = ("overall", "by_type", "monthly", "weekly", "type_month", "type_week", "by_side", "type_side", "weekday", "hour", "year", "quarter")
GROUPS = {"overall": (), "by_type": ("news_type",), "monthly": ("month_chicago",), "weekly": ("week_chicago",),
          "type_month": ("news_type", "month_chicago"), "type_week": ("news_type", "week_chicago"),
          "by_side": ("side",), "type_side": ("news_type", "side"), "weekday": ("weekday_chicago",),
          "hour": ("hour_chicago",), "year": ("year",), "quarter": ("quarter",)}
CENTRAL = {"n": "completed", "mfe": "average_mfe_ticks", "mae": "average_mae_ticks", "close": "average_close_ticks",
           "med": "median_close_ticks", "fav": "favorable_close_percent", "ratio": "mfe_mae_ratio", "support": "sample_support"}
BASE = {"mode": "mode", "h": "horizon_bars"}
SUMMARY_COLUMNS = ("signals", "completed", "pending", "long_signals", "short_signals", "average_mfe_ticks", "average_mae_ticks", "average_close_ticks",
                   "median_mfe_ticks", "median_mae_ticks", "median_close_ticks", "average_mfe_percent", "average_mae_percent", "average_close_percent",
                   "favorable_close_percent", "adverse_close_percent", "flat_close_percent", "mfe_above_mae_percent", "mfe_mae_ratio")
TAIL_COLUMNS = ("completed", *tuple(f"p{q}_{measure}_ticks" for measure in ("mfe", "mae", "close") for q in (10, 25, 75, 90)),
                "median_mfe_ticks", "median_mae_ticks", "median_close_ticks", "min_close_ticks", "max_close_ticks", "sample_support")
DOWNLOAD_PLANS = {
    "summary": (("overall", "by_type", "by_side", "type_side", "weekday", "hour"), SUMMARY_COLUMNS),
    "periods": (("monthly", "weekly", "year", "quarter"), SUMMARY_COLUMNS),
    "event-periods": (("type_month", "type_week"), SUMMARY_COLUMNS), "distributions": (FAMILIES, TAIL_COLUMNS),
}


def require(value, message):
    if not value:
        raise ValueError(message)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def csv_data(path):
    with Path(path).open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames
        require(fields and len(fields) == len(set(fields)), f"{path}: invalid CSV header")
        rows = list(reader)
    require(all(None not in row and all(value is not None for value in row.values()) for row in rows), f"{path}: malformed CSV")
    return fields, rows


def value(raw, percent=False):
    if raw == "":
        return None
    try:
        number = float(raw)
    except (ValueError, TypeError):
        require(not percent, "a percentage source is text")
        return raw
    require(math.isfinite(number), "source cell is nonfinite")
    return number / 100 if percent else number


def same(actual, expected, context, counters):
    if expected is None:
        require(actual is None, f"{context}: null became {actual!r}")
        counters["null_cells"] += 1
    elif isinstance(expected, str):
        require(actual == expected, f"{context}: text changed")
        counters["text_cells"] += 1
    else:
        require(isinstance(actual, (float, int)) and not isinstance(actual, bool) and
                math.isfinite(actual) and math.isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-12),
                f"{context}: {actual!r} differs from {expected!r}")
        counters["numeric_cells"] += 1
        if expected == 0:
            counters["observed_zero_cells"] += 1


def at(document, pointer):
    node = document
    for part in pointer.strip("/").split("/"):
        part = part.replace("~1", "/").replace("~0", "~")
        node = node[int(part)] if isinstance(node, list) else node[part]
    return node


def leaves(node, prefix=""):
    if isinstance(node, dict):
        return {item for key, child in node.items() for item in leaves(child, prefix + "/" + key)}
    if isinstance(node, list):
        return {item for index, child in enumerate(node) for item in leaves(child, prefix + "/" + str(index))}
    return {prefix}


def table_plans():
    central = dict(CENTRAL)
    overview = {key: field for key, field in central.items() if key not in ("support",)}
    plans = {"overview": ("overall", {**BASE, **overview, "pending": "pending", "long": "long_signals", "short": "short_signals"}),
             "news-type": ("by_type", {**BASE, "type": "news_type", **{key: field for key, field in central.items() if key != "support"},
                                              "medmfe": "median_mfe_ticks", "medmae": "median_mae_ticks"}),
             "news-distribution": ("by_type", {**BASE, "type": "news_type", "n": "completed", "mfe10": "p10_mfe_ticks", "mfe90": "p90_mfe_ticks",
                                               "mae50": "median_mae_ticks", "mae90": "p90_mae_ticks", "cl10": "p10_close_ticks", "cl25": "p25_close_ticks",
                                               "cl75": "p75_close_ticks", "cl90": "p90_close_ticks"}),
             "news-rates": ("by_type", {**BASE, "type": "news_type", "n": "completed", "mp": "average_mfe_percent", "ap": "average_mae_percent", "cp": "average_close_percent",
                                        "fav": "favorable_close_percent", "adverse": "adverse_close_percent", "flat": "flat_close_percent", "mabove": "mfe_above_mae_percent", "support": "sample_support"}),
             "elapsed": ("overall", {**BASE, "n": "completed", "mean": "average_elapsed_minutes", "median": "median_elapsed_minutes", "max": "max_elapsed_minutes", "pending": "pending"})}
    for section, family, dims in (("monthly", "monthly", {"period": "month_chicago"}), ("weekly", "weekly", {"period": "week_chicago"}),
                                  ("type-month", "type_month", {"type": "news_type", "period": "month_chicago"}),
                                  ("type-week", "type_week", {"type": "news_type", "period": "week_chicago"}),
                                  ("ema-side", "by_side", {"side": "side"}), ("type-side", "type_side", {"type": "news_type", "side": "side"}),
                                  ("weekday", "weekday", {"day": "weekday_chicago"}), ("hour", "hour", {"hour": "hour_chicago"}),
                                  ("year", "year", {"period": "year"}), ("quarter", "quarter", {"period": "quarter"})):
        plans[section] = (family, {**BASE, **dims, **central})
    return plans


def preservation(stage, pins):
    manifest = read(stage / "import-manifest.json")
    require(len(manifest["files"]) == 146, "expected 146 retained original files")
    retained = set()
    for item in manifest["files"]:
        original = Path(item["original_locator"])
        copy = stage / item["retained_path"]
        require(copy not in retained, "duplicate retained source identity")
        retained.add(copy)
        require(original.is_file() and copy.is_file() and original.stat().st_size == copy.stat().st_size == item["bytes"], f"source size changed: {copy}")
        require(digest(original) == digest(copy) == item["sha256"], f"source bytes changed: {copy}")
        pins[item["retained_path"]] = item["sha256"]
    source = stage / "source-original/per_future_news"
    require({path for path in source.rglob("*") if path.is_file()} == retained, "retained original source inventory differs")
    lock = read(stage / "inputs.lock.json")
    require(len(lock["files"]) == 8, "expected eight frozen source inputs")
    for item in lock["files"]:
        path = source / item["path"]
        require(path.stat().st_size == item["bytes"] and digest(path) == item["sha256"], f"input lock mismatch: {path}")
    return source


def coverage_rows(source, symbol):
    _, all_events = csv_data(source / "study/events.csv")
    _, all_exclusions = csv_data(source / "study/exclusions.csv")
    events = [row for row in all_events if row["symbol"] == symbol and row["mode"] == "combined"]
    excluded = [row for row in all_exclusions if row["symbol"] == symbol and row["mode"] == "combined"]
    result = []
    for category in read(source / f"calendars/{symbol}_archive.json")["category_map"]:
        code = str(category["code"])
        count = sum(row["type_code"] == code for row in events)
        mixed = sum(row["type_code"] == "13" and code in row["component_category_codes"].split(";") for row in events)
        reasons = Counter(row["reason"] for row in excluded if row["category_code"] == code)
        text = [f"{reason}: {n}" for reason, n in sorted(reasons.items())]
        if mixed:
            text.append(f"Also present in {mixed} Mixed timestamp(s); Mixed outcomes are kept exclusive")
        if not count and not mixed and not reasons:
            text.append("No eligible standalone source observations; no effect estimate available")
        result.append({"news_type": category["label"], "eligible_signals": str(count), "excluded": str(sum(reasons.values())),
                       "reason": "; ".join(text) if text else "Eligible standalone observations retained"})
    result.append({"news_type": "Mixed types (same timestamp)", "eligible_signals": str(sum(row["type_code"] == "13" for row in events)),
                   "excluded": "0", "reason": "Exclusive simultaneous selected-category bucket; never exploded into components"})
    return result


def verify(stage):
    pins, counters, publication_counts = {}, Counter(), {}
    source = preservation(stage, pins)
    scientific = read(stage / "scientific-verification.json")
    require(scientific["status"] == "passed", "scientific aggregation has not passed")
    for relative, expected in scientific["output_hashes"].items():
        require(digest(stage / relative) == expected, f"scientifically checked table changed: {relative}")
    config = read(stage / "config.json")
    require(len(config["publication_ids"]) == 6, "expected six explicit publication identities")
    for symbol, identity in zip(SYMBOLS, config["publication_ids"]):
        directory = stage / "publications" / identity
        document = read(directory / "publication.json")
        mapping = read(directory / "source-map.json")
        chart = read(directory / "chart-spec.json")
        require(document["id"] == mapping["publication_id"] == identity and document["source"]["runId"] == config["run_id"], "publication identity differs")
        require(mapping["source_row_base"] == 0 and mapping["run_id"] == config["run_id"], "source-map identity/base differs")
        tables = {family: csv_data(stage / f"tables/{symbol}-{family}.csv")[1] for family in FAMILIES}
        coverage = coverage_rows(source, symbol)
        require(csv_data(stage / f"tables/{symbol}-coverage.csv")[1] == coverage, f"{symbol}: calendar coverage differs")
        tables["coverage"] = coverage
        sections = {section["id"]: (index, section) for index, section in enumerate(document["sections"])}
        require(len(sections) == len(document["sections"]), "duplicate section identity")
        plans = table_plans()
        plans["coverage"] = ("coverage", {"c0": "news_type", "c1": "eligible_signals", "c2": "excluded", "c3": "reason"})
        require({section["id"] for section in document["sections"] if section["kind"] == "table"} == set(plans), "unverified/missing table section")
        projections = [item for item in mapping["projections"] if "sourceRows" in item] + [mapping["coverage"]]
        projection_by_target = {item["target"]: item for item in projections}
        require(len(projection_by_target) == len(projections) == len(plans), "duplicate/missing table projection")
        start_count = sum(counters.values())
        for section_id, (family, fields) in plans.items():
            index, section = sections[section_id]
            projection = projection_by_target[f"/sections/{index}/rows"]
            relative = f"tables/{symbol}-{family}.csv"
            require(projection["artifact"] == relative and projection["sha256"] == digest(stage / relative), "table map pin changed")
            require(projection["sourceRows"] == list(range(len(tables[family]))), "table projection omitted/repeated source rows")
            require(set(projection["columns"]) == set(fields), f"{section_id}: map column coverage differs")
            schema = {column["key"]: column for column in section["columns"]}
            require(len(schema) == len(section["columns"]) and set(schema) == set(fields), f"{section_id}: report columns differ")
            require(len(section["rows"]) == len(tables[family]), f"{section_id}: report rows differ")
            for key, field in fields.items():
                percent = field.endswith("_percent")
                require(projection["columns"][key] == {"column": field, "operation": "percent/100" if percent else "identity"}, "source map semantic mismatch")
                require((schema[key].get("format") == "percent") == percent, f"{section_id}/{key}: percent formatter mismatch")
            for row_index, (actual, original) in enumerate(zip(section["rows"], tables[family])):
                require(set(actual) == set(fields), "table cell coverage differs")
                for key, field in fields.items():
                    expected = value(original[field], field.endswith("_percent"))
                    same(actual[key], expected, f"{identity}/{section_id}/{row_index}/{key}", counters)
                    counters["table_cells"] += 1
            if section.get("rowFilters"):
                filters = {item["key"]: item for item in section["rowFilters"]}
                require(filters["mode"]["defaultValue"] == "combined" and filters["h"]["defaultValue"] == 5, "default saved selectors differ")
        metric_fields = ("completed", "average_mfe_ticks", "average_mae_ticks", "average_close_ticks", "favorable_close_percent", "mfe_mae_ratio")
        h5 = next(row for row in tables["overall"] if row["mode"] == "combined" and row["horizon_bars"] == "5")
        metric_index, snapshot = sections["snapshot"]
        require(snapshot["kind"] == "metrics" and len(snapshot["items"]) == 6, "snapshot metric coverage differs")
        require(len(mapping["metrics"]) == len({item["pointer"] for item in mapping["metrics"]}) == 6, "metric mapping coverage differs")
        for position, field in enumerate(metric_fields):
            percent = field.endswith("_percent")
            item = snapshot["items"][position]
            require((item["format"] == "percent") == percent, "metric percent formatter differs")
            same(item["value"], value(h5[field], percent), f"{identity}/snapshot/{position}", counters)
            target = f"/sections/{metric_index}/items/{position}/value"
            binding = next(item for item in mapping["metrics"] if item["pointer"] == target)
            require(binding["column"] == field and binding["artifact"] == f"tables/{symbol}-overall.csv" and binding["operation"] == ("percent/100" if percent else "identity"), "metric mapping semantics differ")
            counters["metric_cells"] += 1
        expected_chart = {"symbol": symbol, "horizons": {}, "types": [], "months": []}
        for mode in ("combined", "us_only", "local_only"):
            expected_chart["horizons"][mode] = [{"h": value(row["horizon_bars"]), "close": value(row["average_close_percent"]), "n": value(row["completed"])} for row in tables["overall"] if row["mode"] == mode]
        for row in tables["by_type"]:
            if row["mode"] == "combined" and row["horizon_bars"] == "5":
                expected_chart["types"].append({key: value(row[field]) for key, field in (("type", "news_type"), ("mfe", "average_mfe_ticks"), ("mae", "average_mae_ticks"), ("close", "average_close_ticks"), ("n", "completed"))})
        for row in tables["monthly"]:
            if row["mode"] == "combined" and row["horizon_bars"] == "5":
                expected_chart["months"].append({"period": row["month_chicago"], "close": value(row["average_close_percent"]), "n": value(row["completed"])})
        require(leaves(chart) == leaves(expected_chart), "chart source coverage differs")
        for pointer in leaves(expected_chart):
            same(at(chart, pointer), at(expected_chart, pointer), f"{identity}/chart{pointer}", counters)
            counters["chart_cells"] += pointer != "/symbol"
        require({item["pointer"] for item in mapping["chart_bindings"]} == leaves(chart) - {"/symbol"}, "chart map coverage differs")
        for binding in [*mapping["metrics"], *mapping["chart_bindings"]]:
            require(digest(stage / binding["artifact"]) == binding["sha256"], "cell map source hash differs")
            _, rows = csv_data(stage / binding["artifact"])
            expected = value(rows[binding["row"]][binding["column"]], binding["operation"] == "percent/100")
            actual = at(chart if binding in mapping["chart_bindings"] else document, binding["pointer"])
            same(actual, expected, "mapped single cell", counters)
        download_maps = {item["target"]: item for item in mapping["projections"] if "downloadRows" in item}
        require(len(document["downloads"]) == len(download_maps) == 4, "download coverage differs")
        for item in document["downloads"]:
            name = item["id"]
            families, metrics = DOWNLOAD_PLANS[name]
            expected, expected_maps = [], []
            for family in families:
                dims = GROUPS[family]
                period = next((dimension for dimension in dims if dimension in ("month_chicago", "week_chicago", "year", "quarter")), None)
                grouping = [dimension for dimension in dims if dimension != period]
                for index, row in enumerate(tables[family]):
                    expected.append({"family": family, "mode": row["mode"], "horizon_bars": row["horizon_bars"], "group": " | ".join(row[dimension] for dimension in grouping) if grouping else "All events", "period": row[period] if period else "", **{field: row[field] for field in metrics}})
                    expected_maps.append({"family": family, "row": index, "groupColumns": grouping, "periodColumn": period})
            relative = f"tables/{symbol}-download-{name}.csv"
            target = f"downloads/{symbol.lower()}-{name}.csv"
            require(item["path"] == target and item["source"]["artifact"] == relative, "unexpected selected CSV source/target")
            headers, rows = csv_data(directory / target)
            require(rows == expected and headers == ["family", "mode", "horizon_bars", "group", "period", *metrics], "download saved strings/coverage differ")
            require(headers == item["columns"] and len(rows) == item["rowCount"], "download shape metadata differs")
            require((directory / target).read_bytes() == (stage / relative).read_bytes(), "selected CSV copy differs")
            require(digest(directory / target) == item["sha256"] == item["source"]["sha256"], "selected CSV declared hash differs")
            mapping_item = download_maps[target]
            require(mapping_item["downloadRows"] == expected_maps and mapping_item["metricColumns"] == list(metrics), "download map rows/metrics differ")
            require(mapping_item["artifact"] == relative and mapping_item["sha256"] == digest(stage / relative), "download map source pin differs")
            require(set(mapping_item["sources"]) == set(families), "download family source coverage differs")
            for family, pin in mapping_item["sources"].items():
                require(pin["artifact"] == f"tables/{symbol}-{family}.csv" and pin["sha256"] == digest(stage / pin["artifact"]), "download family pin differs")
            counters["download_cells"] += len(rows) * len(headers)
            counters["download_rows"] += len(rows)
            counters["downloads"] += 1
            pins[f"publications/{identity}/{target}"] = digest(directory / target)
        figures = [section for section in document["sections"] if section["kind"] == "figure"]
        require({section["path"] for section in figures} == {f"figures/{name}.png" for name in ("horizon-comparison", "news-type-excursions", "monthly-direction")}, "figure coverage differs")
        for section in figures:
            path = directory / section["path"]
            header = path.read_bytes()[:24]
            require(header[:8] == b"\x89PNG\r\n\x1a\n" and min(struct.unpack(">II", header[16:24])) > 500, "invalid/undersized selected figure")
            counters["figures"] += 1
            pins[f"publications/{identity}/{section['path']}"] = digest(path)
        for reference in document["references"]:
            require(reference["runId"] == config["run_id"] and digest(stage / reference["artifact"]) == reference["sha256"], "saved reference pin differs")
            counters["references"] += 1
        for name in ("publication.json", "source-map.json", "chart-spec.json"):
            pins[f"publications/{identity}/{name}"] = digest(directory / name)
        counters["publications"] += 1
        publication_counts[identity] = {"table_rows": sum(len(sections[key][1]["rows"]) for key in plans), "checked_counter_delta": sum(counters.values()) - start_count}
    return {"status": "passed", "result": "passed", "scope": "Independent selected publication transfer and original-source preservation audit. Numerical aggregation has a separate scientific receipt; PNG bytes/shape and saved chart inputs are checked, not rendered pixel meaning or economic claims.",
            "counts": dict(counters), "publication_counts": publication_counts, "retained_source_files": 146, "input_lock_files": 8,
            "source_and_output_hashes": pins, "scientific_receipt_sha256": digest(stage / "scientific-verification.json")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", type=Path)
    stage = parser.parse_args().stage.resolve()
    require(stage.is_dir() and stage.parent.name == "25_forex_news_ema" and stage.parent.parent.name == "work", "explicit study-25 staging target required")
    try:
        receipt = verify(stage)
    except (ValueError, OSError, KeyError, TypeError, StopIteration) as exc:
        receipt = {"status": "failed", "result": "failed", "error": str(exc)}
    receipt.update(checker_path=str(Path(__file__).resolve()), checker_sha256=digest(__file__),
                   executed_at_utc=datetime.now(timezone.utc).isoformat(), command=[sys.executable, str(Path(__file__).resolve()), str(stage)])
    (stage / "independent-publication-audit.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps({key: receipt[key] for key in ("status", "counts", "retained_source_files", "input_lock_files", "error") if key in receipt}))
    return 0 if receipt["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
