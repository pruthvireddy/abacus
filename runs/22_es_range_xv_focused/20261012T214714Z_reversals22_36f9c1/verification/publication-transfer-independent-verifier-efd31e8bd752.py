"""Independent saved-publication transfer verification; no research imports.

This script checks selected report projections and original CSV strings against
already-saved tables. It does not recompute reversal events or market outcomes.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
from decimal import Decimal, localcontext
import hashlib
import json
from pathlib import Path
import sys


COHORTS = ("all", *(str(n) for n in range(1, 11)), "11-15", "16-20", "21+", "unknown_start")
YEARS = ("", *(str(n) for n in range(2019, 2027)))
WINDOWS = ("all_hours", "asia", "london", "ny", "asia_open", "ny_open", "ny_am", "ny_pm")
WINDOW_LABELS = dict(zip(WINDOWS, ("All hours", "Asia", "London", "NY", "Asia Open", "NY Open", "NY AM", "NY PM")))
DIRECTIONS = ("bullish", "bearish", "all")
DIRECTION_LABELS = {"bullish": "Bullish reversal", "bearish": "Bearish reversal", "all": "Both directions"}
GROUP = ("year", "timeframe_id", "direction", "prior_leg_bucket")
TABLES = {"tables/reversal_summary.csv": 9720, "tables/reversal_continuation.csv": 194400,
          "tables/reversal_retracement.csv": 38880, "tables/coverage.csv": 216}
CONT_SOURCE = "tables/reversal_continuation.csv"
RETRACE_SOURCE = "tables/reversal_retracement.csv"
SUMMARY_SOURCE = "tables/reversal_summary.csv"
PIVOTS = {"probabilities.csv": "probability", "successes.csv": "numerator",
          "known-outcomes.csv": "denominator", "unknown-outcomes.csv": "unknown_count"}
RETRACE_FIELDS = (*GROUP, "level_percent", "event_count", "valid_f1_count", "unknown_f1_count", "touch_count",
                  "touch_probability", "joint_beyond_close_numerator", "joint_beyond_close_denominator",
                  "joint_beyond_close_probability", "conditional_beyond_close_numerator",
                  "conditional_beyond_close_denominator", "conditional_beyond_close_probability")
SUMMARY_FIELDS = (*GROUP, "event_count", "exact_followup_count", "censored_followup_count", "known_f1_count",
                  "unknown_f1_count", "prior_start_known_count", "prior_start_unknown_count", "sessions_with_events",
                  "sessions_with_known_f1", "eligible_bar_count", "covered_sessions", "first_session_date",
                  "last_session_date", "bar_coverage_anchor", "event_membership_anchor")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def regular(path):
    require(path.is_file() and not any(parent.is_symlink() for parent in (path, *path.parents)),
            f"regular non-symlink file required: {path}")
    return path


def read_json(path):
    return json.loads(regular(path).read_text())


def read_csv(path):
    with regular(path).open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        rows = list(reader)
        require(reader.fieldnames is not None and len(reader.fieldnames) == len(set(reader.fieldnames)),
                f"invalid CSV columns: {path}")
        require(all(None not in row and all(value is not None for value in row.values()) for row in rows),
                f"invalid CSV row width: {path}")
        return reader.fieldnames, rows


def year_label(year):
    return "All years" if year == "" else f"{year} (partial)" if year in ("2019", "2026") else year


def leg_label(cohort):
    if cohort == "all":
        return "All preceding legs"
    if cohort == "unknown_start":
        return "Unknown start"
    return cohort + (" candle" if cohort == "1" else " candles")


def numeric(raw):
    if raw == "":
        return None
    with localcontext() as context:
        context.prec = 50
        value = Decimal(raw)
        require(value.is_finite(), "nonfinite source numeric value")
        return value.quantize(Decimal("0.000001"))


def expected_source(section, column):
    if section == "coverage":
        return SUMMARY_SOURCE, None
    if section.startswith("counts-"):
        return SUMMARY_SOURCE, {"e": "event_count", "f": "known_f1_count", "u": "unknown_f1_count",
                                "c": "censored_followup_count", "s": "sessions_with_events"}[column]
    if section.startswith("overall-"):
        return CONT_SOURCE, {"n": "n", "s": "numerator", "d": "denominator", "u": "unknown_count", "p": "probability"}[column]
    if section.startswith("n"):
        return CONT_SOURCE, "probability"
    if section == "overall" or section.startswith("depth-"):
        return RETRACE_SOURCE, {"l": "level_percent", "f": "valid_f1_count", "u": "unknown_f1_count",
                               "t": "touch_count", "p": "touch_probability", "j": "joint_beyond_close_numerator",
                               "q": "joint_beyond_close_probability", "r": "conditional_beyond_close_probability"}[column]
    raise ValueError(f"unexpected numeric section {section}")


def verify_context(section, target_row, source_row, setting, target_index):
    require(source_row["setting_ticks"] == str(setting), f"wrong source chart in {section}")
    if section == "coverage":
        require(tuple(source_row[key] for key in GROUP) == ("", "all_hours", "all", "all"),
                "coverage metrics do not use overall pooled-direction source")
    elif section.startswith("overall-"):
        direction = section[len("overall-"):]
        require(tuple(source_row[key] for key in GROUP) == ("", "all_hours", direction, "all"),
                f"wrong overall source context in {section}")
        require(target_row["direction"] == DIRECTION_LABELS[direction], f"wrong direction label in {section}")
        require(source_row["n"] == str(target_index + 1), f"wrong n order in {section}")
    elif section == "overall":
        direction = DIRECTIONS[target_index // 4]
        level = (25, 50, 75, 100)[target_index % 4]
        require(tuple(source_row[key] for key in GROUP) == ("", "all_hours", direction, "all"),
                "wrong overall retracement context")
        require(target_row["direction"] == DIRECTION_LABELS[direction], "wrong overall retracement direction label")
        require(source_row["level_percent"] == str(level), "wrong overall retracement level")
    else:
        direction = section.rsplit("-", 1)[1]
        require(source_row["direction"] == direction, f"wrong direction source in {section}")
        expected = {"year": year_label(source_row["year"]), "window": WINDOW_LABELS[source_row["timeframe_id"]],
                    "leg": leg_label(source_row["prior_leg_bucket"])}
        require(all(target_row[key] == value for key, value in expected.items()), f"wrong context labels in {section}, row {target_index}")
        if section.startswith("depth-"):
            require(source_row["level_percent"] == section.split("-")[1], f"wrong source depth in {section}")


def audit(stage, workspace, prior_path):
    script = regular(Path(__file__).resolve())
    script_sha = digest(script)
    verify_dir = stage / "verification"
    verify_dir.mkdir(exist_ok=True)
    snapshot = verify_dir / f"publication-transfer-independent-verifier-{script_sha[:12]}.py"
    if snapshot.exists():
        require(digest(snapshot) == script_sha, "retained verifier differs")
    else:
        with snapshot.open("xb") as stream:
            stream.write(script.read_bytes())
    artifact_hashes = {snapshot.relative_to(stage).as_posix(): script_sha}
    source_data = {}
    for name, expected_rows in TABLES.items():
        header, rows = read_csv(stage / name)
        require(len(rows) == expected_rows, f"wrong saved source row count: {name}")
        source_data[name] = rows
        artifact_hashes[name] = digest(stage / name)
    stage_receipt = read_json(stage / "publication-verification.json")
    require(stage_receipt["result"] == "passed" and stage_receipt["run_id"] == stage.name, "wrong producer publication receipt")
    for name, expected in stage_receipt["artifact_hashes"].items():
        require(digest(regular(stage / name)) == expected, f"producer receipt hash changed: {name}")
        artifact_hashes[name] = expected
    artifact_hashes["publication-verification.json"] = digest(stage / "publication-verification.json")

    counts = {"publications": 0, "numeric_cells": 0, "context_tables": 0, "context_rows": 0,
              "overall_rows": 0, "selected_csv_files": 0, "selected_csv_rows": 0, "original_csv_cells": 0,
              "source_tables": len(TABLES), "source_rows": sum(TABLES.values()), "prior_publication_files": 0}
    publication_results = []
    expected_contexts = [(year_label(year), WINDOW_LABELS[window], leg_label(cohort))
                         for year in YEARS for window in WINDOWS for cohort in COHORTS]
    expected_context_keys = [(year, window, direction, cohort)
                             for year in YEARS for window in WINDOWS for direction in DIRECTIONS for cohort in COHORTS]
    required_folders = {f"{setting}t-{kind}" for setting in (4, 5, 6) for kind in ("continuation", "retracement")}
    folders = sorted(path for path in (stage / "publications").iterdir() if path.is_dir())
    require({path.name for path in folders} == required_folders, "six chart/view folders required")
    for folder in folders:
        setting = int(folder.name[0])
        kind = folder.name.split("-", 1)[1]
        report = read_json(folder / "publication.json")
        mapping = read_json(folder / "source-map.json")
        receipt = read_json(folder / "verification.json")
        require(report["source"] == {"producer": "sahadeva", "runId": stage.name}, f"wrong report attribution: {folder.name}")
        require(report["id"] == f"es-range-xv-reversal-{kind}-{setting}t-20261012", f"wrong report identity: {folder.name}")
        require(report["title"].startswith(f"ES {setting} RXV"), f"wrong report chart title: {folder.name}")
        require(mapping["run_id"] == stage.name and mapping["schema_version"] == 1, "wrong source map identity")
        require(mapping["source_hashes"] == {name: artifact_hashes[name] for name in TABLES}, "wrong source map table hashes")
        require(receipt["result"] == "passed" and receipt["publication_sha256"] == digest(folder / "publication.json"), "wrong report verification SHA")
        sections = {section["id"]: section for section in report["sections"]}
        require(len(sections) == len(report["sections"]), "duplicate report sections")
        full_sections = [section for section in sections.values() if section["kind"] == "table" and "year" in section["rows"][0]]
        require(len(full_sections) == 8, f"eight complete context tables required in {folder.name}")
        for section in full_sections:
            rows = section["rows"]
            require(len(rows) == 1080, f"wrong full table rows in {folder.name}/{section['id']}")
            require([(row["year"], row["window"], row["leg"]) for row in rows] == expected_contexts,
                    f"context order/coverage differs in {folder.name}/{section['id']}")
            require([column["label"] for column in section["columns"][:3]] == ["Year", "Window", "Preceding leg"],
                    f"wrong Year/Window/Leg column labels in {folder.name}/{section['id']}")
            counts["context_tables"] += 1
            counts["context_rows"] += len(rows)
        expected_addresses = set()
        for section in sections.values():
            if section["kind"] == "metrics":
                for index, item in enumerate(section["items"]):
                    require(item["value"] is None or (isinstance(item["value"], (int, float)) and not isinstance(item["value"], bool)), "invalid metric numeric type")
                    expected_addresses.add((section["id"], "value", index))
            elif section["kind"] == "table":
                if section not in full_sections:
                    counts["overall_rows"] += len(section["rows"])
                numeric_columns = [column["key"] for column in section["columns"] if column.get("format") in ("number", "percent")]
                for index, row in enumerate(section["rows"]):
                    for column in numeric_columns:
                        require(row[column] is None or (isinstance(row[column], (int, float)) and not isinstance(row[column], bool)), "invalid table numeric type")
                        expected_addresses.add((section["id"], column, index))
                    require({key for key, value in row.items() if isinstance(value, (int, float)) and not isinstance(value, bool)} <= set(numeric_columns),
                            "numeric table value lacks a declared numeric column")
        visited = set()
        for binding in mapping["bindings"]["numeric_projections"]:
            section_id, column, source_name, source_column = (binding[key] for key in ("section", "column", "source", "source_column"))
            require(binding["transform"] == "blank_to_null_else_numeric_rounded_six_decimals", "unexpected projection transform")
            expected_name, expected_column = expected_source(section_id, column)
            require(source_name == expected_name and (expected_column is None or source_column == expected_column),
                    f"wrong numeric source declaration {folder.name}/{section_id}/{column}")
            section = sections[section_id]
            for destination_index, physical_source_row in binding["row_pairs"]:
                address = (section_id, column, destination_index)
                require(address in expected_addresses and address not in visited, f"missing/duplicate/extra numeric binding: {address}")
                visited.add(address)
                require(type(physical_source_row) is int and 2 <= physical_source_row <= len(source_data[source_name]) + 1, "unsafe source row number")
                source_row = source_data[source_name][physical_source_row - 2]
                target_row = section["items"][destination_index] if section["kind"] == "metrics" else section["rows"][destination_index]
                verify_context(section_id, target_row, source_row, setting, destination_index)
                if section_id == "coverage":
                    require(source_column == ("event_count", "covered_sessions", "eligible_bar_count", "unknown_f1_count")[destination_index], "wrong coverage metric source")
                if section_id.startswith("n"):
                    require(source_row["n"] == column[1:], f"wrong horizon projection in {section_id}/{column}")
                actual, expected = target_row[column], numeric(source_row[source_column])
                require((actual is None and expected is None) or (actual is not None and expected is not None and Decimal(str(actual)) == expected),
                        f"display numeric differs: {folder.name}/{section_id}/{destination_index}/{column}")
        require(visited == expected_addresses, f"incomplete numeric coverage: {folder.name}")
        require(len(visited) == receipt["numeric_cells_checked"], "producer numeric check count differs")
        counts["numeric_cells"] += len(visited)
        if kind == "continuation":
            for direction in ("bullish", "bearish"):
                columns = [column["key"] for section in full_sections if section["id"].endswith("-" + direction) and section["id"].startswith("n")
                           for column in section["columns"] if column["key"].startswith("n")]
                require(columns == [f"n{n}" for n in range(1, 21)], "n=1..20 coverage is incomplete")
        else:
            for direction in ("bullish", "bearish"):
                require([section["id"] for section in full_sections if section["id"].endswith("-" + direction)]
                        == [f"depth-{n}-{direction}" for n in (25, 50, 75, 100)], "retracement depth coverage is incomplete")

        download_bindings = {row["download"]: row for row in mapping["bindings"]["downloads"]}
        download_descriptors = {Path(row["path"]).name: row for row in report["downloads"]}
        expected_downloads = set(PIVOTS) if kind == "continuation" else {"retracement-recovery.csv", "reversal-samples.csv"}
        require(set(download_bindings) == set(download_descriptors) == expected_downloads, "wrong selected CSV allowlist")
        require({path.name for path in (folder / "downloads").glob("*")} == expected_downloads, "unlisted or missing selected CSV")
        for name in sorted(expected_downloads):
            download = folder / "downloads" / name
            descriptor, binding = download_descriptors[name], download_bindings[name]
            require(descriptor["path"] == f"downloads/{name}" and descriptor["mediaType"] == "text/csv", "wrong CSV descriptor path/media type")
            require(descriptor["sha256"] == binding["sha256"] == digest(download), "wrong CSV descriptor/map SHA")
            source_name = CONT_SOURCE if kind == "continuation" else RETRACE_SOURCE if name == "retracement-recovery.csv" else SUMMARY_SOURCE
            require(binding["source"] == source_name and descriptor["source"] == {"runId": stage.name, "artifact": source_name, "sha256": artifact_hashes[source_name]}, "wrong CSV source attribution")
            source_rows = [(index + 2, row) for index, row in enumerate(source_data[source_name]) if row["setting_ticks"] == str(setting)]
            if kind == "continuation":
                require(binding["pivot_group"] == list(GROUP) and binding["pivot_horizon"] == "n" and binding["setting_ticks"] == setting
                        and binding["source_column"] == PIVOTS[name], "wrong CSV pivot declaration")
                expected_header = (*GROUP, *(f"n{n}" for n in range(1, 21)))
                expected_by_group = {}
                for _, source_row in source_rows:
                    key = tuple(source_row[field] for field in GROUP)
                    target = expected_by_group.setdefault(key, dict(zip(GROUP, key)))
                    horizon = f"n{source_row['n']}"
                    require(horizon not in target, "duplicate saved pivot group/horizon")
                    target[horizon] = source_row[PIVOTS[name]]
                require(list(expected_by_group) == expected_context_keys, "saved CSV pivot context coverage/order differs")
                expected_rows = list(expected_by_group.values())
            else:
                expected_header = RETRACE_FIELDS if name == "retracement-recovery.csv" else SUMMARY_FIELDS
                require(binding["columns"] == list(expected_header) and binding["source_rows"] == [index for index, _ in source_rows], "wrong original-string CSV selection")
                expected_rows = [{key: row[key] for key in expected_header} for _, row in source_rows]
                require({tuple(row[field] for field in GROUP) for row in expected_rows} == set(expected_context_keys), "saved CSV context coverage differs")
            header, rows = read_csv(download)
            require(header == list(expected_header) == descriptor["columns"], "wrong download CSV columns")
            require(rows == expected_rows, f"original CSV strings differ: {folder.name}/{name}")
            require(len(rows) == descriptor["rowCount"] == (12960 if name == "retracement-recovery.csv" else 3240), "wrong selected CSV rows")
            require(binding["original_strings_verified"] is True, "producer original-string flag missing")
            counts["selected_csv_files"] += 1
            counts["selected_csv_rows"] += len(rows)
            counts["original_csv_cells"] += len(rows) * len(header)
            artifact_hashes[download.relative_to(stage).as_posix()] = digest(download)
        require(receipt["csv_files_checked"] == len(expected_downloads) and receipt["original_csv_strings_verified"] is True, "producer CSV count/flag differs")
        for name in ("publication.json", "source-map.json", "verification.json"):
            artifact_hashes[(folder / name).relative_to(stage).as_posix()] = digest(folder / name)
        counts["publications"] += 1
        publication_results.append({"folder": folder.name, "numeric_cells": len(visited), "complete_context_tables": 8,
                                    "selected_csv_files": len(expected_downloads), "publication_sha256": digest(folder / "publication.json")})

    prior = read_json(prior_path)
    require(isinstance(prior, list) and len(prior) == 84, "expected 84 prior publication artifacts")
    require(len({row["path"] for row in prior}) == len(prior), "duplicate retained prior publication locator")
    for row in prior:
        require(digest(regular(workspace / row["path"])) == row["sha256"], f"prior public artifact changed: {row['path']}")
        counts["prior_publication_files"] += 1
    require(digest(script) == digest(snapshot) == script_sha, "verifier bytes changed during check")
    for name, expected in artifact_hashes.items():
        require(digest(regular(stage / name)) == expected, f"checked bytes changed during transfer audit: {name}")
    result = {"schema_version": 1, "result": "passed", "run_id": stage.name,
              "checked_at": datetime.now(timezone.utc).isoformat(), "counts": counts,
              "publications": publication_results, "artifact_hashes": artifact_hashes,
              "command": {"argv": [sys.executable, *sys.argv], "cwd": str(Path.cwd()), "python": sys.version,
                          "implementation": sys.implementation.name, "optimize": sys.flags.optimize},
              "verifier": {"workspace_path": script.relative_to(workspace).as_posix(), "sha256": script_sha,
                           "retained_path": snapshot.relative_to(stage).as_posix()},
              "prior_publication_inventory": {"path": prior_path.relative_to(workspace).as_posix(),
                                               "sha256": digest(prior_path), "verified_files": prior},
              "scope": ["Saved numerical tables to selected publication transfer only; no engine/reporter imports or market-data reanalysis.",
                        "Every displayed numeric cell independently checked using Decimal rounding to six decimals; complete context coverage, labels, chart/direction/horizon identities and all original selected CSV strings checked.",
                        "Prior publication hashes checked unchanged at audit time; this does not certify numerical findings or hosting behavior."]}
    output = verify_dir / "publication-transfer-independent.json"
    with output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write("\n")
    return counts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--prior", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps({"result": "passed", "counts": audit(args.stage.resolve(), args.workspace.resolve(), args.prior.resolve())}))
        return 0
    except (OSError, ValueError, KeyError, IndexError) as exc:
        print(f"Independent publication transfer audit refused: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
