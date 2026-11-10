"""Build, verify and publish the local Daily Facts 1.0.0 release."""
from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from datetime import date, datetime, timezone
import json
from pathlib import Path
import shutil
import sys

import numpy as np
import pyarrow as pa
import pyarrow.dataset as ds
import pyarrow.parquet as pq

from .calendar import holiday_sessions
from .continuous_loader import open_continuous_dataset
from .daily_context import load_daily_context
from .daily_facts import (MINUTE_COLUMNS, context_facts, minute_arrays, minute_groups,
                          output_schema, previous_weekday, session_facts, weekday_roster,
                          window_bounds)
from .daily_facts_loader import ASSETS, DATA_PATH, DATASET_ID, VERSION, load_daily_facts
from .daily_facts_verify import SAMPLE_DAYS, verify_tables
from .manifest_selection import read_pinned_manifest, selected_files
from .paths import resolve_publication_root, workspace_root
from .provenance import (git_version, publication_sources, retain_sources, sha256_file,
                         verify_retained_sources)
from .publication_safety import check_absent, check_path, write_new_bytes

START, END = date(2021, 6, 28), date(2026, 9, 19)
REQUEST = Path(f"requests/inbox/{DATASET_ID}.yaml")
FULFILLED_REQUEST = Path(f"requests/fulfilled/{DATASET_ID}.yaml")
SCHEMA = Path(f"catalog/schemas/{DATASET_ID}.json")
MANIFEST = Path(f"catalog/datasets/{DATASET_ID}.json")
QUALITY = Path(f"reports/quality/{DATASET_ID}.md")
MINUTE_MANIFEST = Path("catalog/datasets/volume_lead_unadjusted_v1.json")
SCHEDULE = Path("data/curated/continuous/1m/roll=volume_lead_v1/roll_schedule.parquet")
CONTEXT_MANIFEST = Path("catalog/datasets/tradingview_daily_context__1.0.0.json")
CALENDAR = Path("catalog/calendars/cme_fixed_clock_session_v1.json")
AUDIT = Path("reports/quality/daily-facts-v1-input-audit-20261108/coverage_by_window.csv")
SYMBOLS = {"ES": "VIX", "NQ": "VXN", "GC": "GVZ"}
PINS = {
    REQUEST: "480fc50a932b6c055f53243512b9b94cb47574a0a25dd23ce3caa1ab9ce76135",
    MINUTE_MANIFEST: "00757f5fc8278e75744d7adfaddc688be588d619d82b1dc1811aa60f21b7e5d4",
    SCHEDULE: "0149b99b75da1138454e5face6516184ace3fef819b324183448c678460621b0",
    CONTEXT_MANIFEST: "b7395d6ec2a3263e6f17b2ed95d22ea235d543a01e5b7f850eff81604ba6ce8f",
    CALENDAR: "d5e9d7895f02c5c66a2231e3f79e6bfbc21cd7ce7aa2f42974cfa50492186bcf",
    AUDIT: "4ff27dde34a59c25c11e0e56c7e518dbf2ca241bf0b09b57c3aab5abfb0a94c7",
}


def _json(value):
    return (json.dumps(value, indent=2, allow_nan=False) + "\n").encode()


def _record(root, path):
    return {"path": str(path.relative_to(root)), "bytes": path.stat().st_size,
            "sha256": sha256_file(path)}


def _pin(root, relative, expected):
    path = check_path(root / relative, root)
    record = _record(root, path)
    if record["sha256"] != expected:
        raise ValueError(f"Daily Facts input SHA-256 mismatch: {relative}")
    return record


@dataclass
class Inputs:
    datasets: dict
    mappings: dict
    calendar: dict
    holidays: dict
    contexts: dict
    context_symbols: dict
    audit: dict
    records: dict

    def identity(self, asset, day):
        matches = [row for row in self.mappings[asset]
                   if row["mapping_start"] <= day < row["mapping_end"]]
        if len(matches) != 1:
            raise ValueError(f"expected exactly one pinned contract for {asset}/{day}")
        row = matches[0]
        return row["new_instrument_id"], row["new_raw_symbol"], row["roll_id"]

    def calendar_status(self, asset, day):
        if not START <= day < END:
            return "outside_pilot", ["outside_pilot"]
        regimes = self.calendar["product_regimes"][asset]
        matching = [regime for regime in regimes
                    if date.fromisoformat(regime["start"]) <= day
                    < date.fromisoformat(regime["end_exclusive"])]
        if len(matching) != 1 or not matching[0]["supported"]:
            return "unsupported_calendar", ["unsupported_calendar"]
        reasons = self.holidays[asset].get(day, [])
        return ("calendar_excluded", reasons) if reasons else ("eligible", [])


def read_inputs(root, workspace):
    records = {"workspace": [_pin(workspace, relative, PINS[relative])
                             for relative in (REQUEST, AUDIT)],
               "publication": [_pin(root, relative, PINS[relative])
                               for relative in (MINUTE_MANIFEST, SCHEDULE, CONTEXT_MANIFEST, CALENDAR)]}
    minute_manifest = read_pinned_manifest(root, MINUTE_MANIFEST, PINS[MINUTE_MANIFEST], True)
    selected_files(root, minute_manifest, lambda path: path == str(SCHEDULE), verify=True)
    schedule = pq.read_table(root / SCHEDULE).to_pylist()
    calendar = json.loads((root / CALENDAR).read_bytes())
    context_manifest = json.loads((root / CONTEXT_MANIFEST).read_bytes())
    context_definition = Path(context_manifest["schema_path"])
    records["publication"].append(_pin(root, context_definition, context_manifest["schema_sha256"]))
    datasets, contexts, context_symbols = {}, {}, {}
    for asset, symbol in SYMBOLS.items():
        dataset = open_continuous_dataset(root, asset, manifest_path=MINUTE_MANIFEST,
                                          expected_manifest_sha256=PINS[MINUTE_MANIFEST],
                                          verify_selected_files=True)
        paths = {str(Path(file).relative_to(root)) for file in dataset.files}
        records["publication"].extend(record for record in minute_manifest["output_files"]
                                      if record["path"] in paths)
        datasets[asset] = dataset
        context = context_manifest["assets"][symbol]
        expected_path = Path("data/features/bars/1d/feature_set=tradingview_daily_context"
                             f"/version=1.0.0/asset={symbol}/part-000.parquet")
        if context["output_path"] != str(expected_path):
            raise ValueError(f"unexpected pinned context locator for {symbol}")
        record = _pin(root, expected_path, context["output_sha256"])
        if record["bytes"] != context["output_bytes"]:
            raise ValueError(f"unexpected pinned context size for {symbol}")
        records["publication"].append(record)
        rows = load_daily_context(root, symbol, version="1.0.0",
                                  columns=("trading_day", "available_at", "close")).to_pylist()
        timestamps = [row["available_at"] for row in rows]
        if (len(rows) != context["published_rows"] or any(value is None for value in timestamps)
                or any(left >= right for left, right in zip(timestamps, timestamps[1:]))):
            raise ValueError(f"invalid retained context ordering or count for {symbol}")
        contexts[asset], context_symbols[asset] = rows, context["source_symbol"]
    with (workspace / AUDIT).open(newline="") as handle:
        audit = {(r["asset"], r["window"]): r for r in csv.DictReader(handle)
                 if r["scope"] == "common_supported_normal"}
    return Inputs(datasets, {a: [r for r in schedule if r["product"] == a] for a in ASSETS},
                  calendar, {a: holiday_sessions(a, START.year, END.year) for a in ASSETS},
                  contexts, context_symbols, audit, records)


def check_input_records(root, workspace, records):
    for key, base in (("workspace", workspace), ("publication", root)):
        for record in records[key]:
            actual = _pin(base, Path(record["path"]), record["sha256"])
            if actual["bytes"] != record["bytes"]:
                raise ValueError(f"Daily Facts input size changed: {record['path']}")


def build_asset(asset, inputs, days):
    calculation_days = sorted(set(days) | {previous_weekday(day) for day in days
                                           if previous_weekday(day) >= START})
    dataset = inputs.datasets[asset]
    context_rows = inputs.contexts[asset]
    context_index = 0
    calculated = {}
    for year in sorted({day.year for day in calculation_days}):
        year_days = [day for day in calculation_days if day.year == year]
        predicate = (ds.field("year") == year) & ds.field("session_date").isin(year_days)
        table = dataset.to_table(columns=list(MINUTE_COLUMNS), filter=predicate)
        empty = minute_arrays(table.slice(0, 0))
        minutes = dict(minute_groups(table))
        for day in year_days:
            prior = previous_weekday(day)
            identity = inputs.identity(asset, day)
            prior_identity = inputs.identity(asset, prior)
            status, reasons = inputs.calendar_status(asset, day)
            row = session_facts(asset, day, minutes.get(day, empty), identity, prior_identity,
                                identity != prior_identity, inputs.calendar["calendar_id"],
                                status, reasons, calculated.get(prior))
            cutoff = window_bounds(asset, day)["rth"][0]
            while (context_index < len(context_rows)
                   and context_rows[context_index]["available_at"] <= cutoff):
                context_index += 1
            source = context_rows[context_index - 1] if context_index else None
            row.update(context_facts(source, SYMBOLS[asset], inputs.context_symbols[asset], cutoff, status))
            calculated[day] = row
    return pa.Table.from_pylist([calculated[day] for day in days], schema=output_schema())


def _schema_contract():
    schema = output_schema()
    return {
        "dataset_id": DATASET_ID, "version": VERSION,
        "primary_key": ["release_id", "asset", "session_date"],
        "columns": [{"name": field.name, "type": str(field.type), "nullable": field.nullable}
                    for field in schema],
        "metadata": {key.decode(): value.decode() for key, value in schema.metadata.items()},
        "timing": {"window_open": "<window>_open_available_at",
                   "window_aggregates": "<window>_aggregate_available_at",
                   "prior_close": "prior_rth_close_available_at",
                   "gap": "rth_gap_available_at", "volatility_context": "vol_index_available_at",
                   "vwap_and_volume_comparisons": "<field>_available_at"},
        "quality": "Coverage counts describe retrospective window inspection. Status fields qualify nulls.",
        "window_prefixes": ["globex", "overnight", "rth", "or15", "first60", "last60"],
        "units": {"price_points": "decimal128(20,9)", "volume": "contracts",
                  "returns_and_ratios": "fraction", "vwap_and_distance": "price points"},
    }


def _quality_report(result, row_counts, manifest_pin_labels):
    rows = ["# Daily Facts 1.0.0 local release", "",
            "The release contains one row per asset and weekday from June 28, 2021 through "
            "September 18, 2026. Calendar exclusions remain in the roster. Each window has "
            "its own completeness, opening readiness and logical availability.", "",
            "## Verified coverage", "",
            "| Asset | Window | Complete | Eligible | Missing minutes |",
            "|---|---|---:|---:|---:|"]
    for row in result["coverage"]:
        rows.append(f"| {row['asset']} | {row['window']} | {row['complete']:,} | "
                    f"{row['eligible']:,} | {row['missing_minutes']:,} |")
    rows += ["", f"The release contains {sum(row_counts.values()):,} rows and matches all "
             "21 audited window and prefix aggregates, including missing-minute totals. "
             f"An independent retained-source comparison passed on {len(result['independent_source_sessions'])} "
             "asset sessions covering exact prices, contract volumes, rational VWAP, "
             "gaps, context and availability.", "",
             "Exact prices use decimal points at nine decimal places. Derived fractional "
             "and VWAP values are stored as float64 and checked with relative tolerance "
             "1e-12 and absolute tolerance 1e-9. Logical timing uses the retained snapshots. "
             "Historical provider vintages and actual dissemination timing are unverified.", "",
             "The preceding weekday supplies the opening reference when eligible and on "
             "the same contract. An excluded weekday, incomplete RTH, a roll or the pilot "
             "boundary leaves the reference empty.", "",
             f"The manifest inventories {manifest_pin_labels} pinned input files, output "
             "Parquet, schema, quality and the retained producer sources.", "",
             f"[Manifest](../../{MANIFEST}) · [Schema](../../{SCHEMA}) · "
             f"[Frozen request](../../{FULFILLED_REQUEST}) · "
             "[Input audit](daily-facts-v1-input-audit-20261108/README.md)", ""]
    return "\n".join(rows).encode()


def _verify(inputs, tables, days, full):
    return verify_tables(tables, inputs.datasets, days, inputs.audit, inputs.identity,
                         inputs.calendar_status, inputs.contexts, full=full)


def _publication_leaves(root):
    data_dir = root / DATA_PATH
    return [data_dir, *[root / relative for relative in (SCHEMA, QUALITY, MANIFEST, FULFILLED_REQUEST)]]


def _preflight_publication(root, workspace):
    for path in _publication_leaves(root):
        check_absent(path, root)
        if path != root / DATA_PATH:
            check_absent(path.with_name(path.name + ".part"), root)
    check_absent(workspace / FULFILLED_REQUEST, workspace)
    check_absent((workspace / FULFILLED_REQUEST).with_suffix(".yaml.part"), workspace)


def _promote(root, workspace, stage, manifest):
    _preflight_publication(root, workspace)
    data_dir = root / DATA_PATH
    data_dir.mkdir(parents=True, exist_ok=False)
    for record in manifest["output_files"]:
        relative = Path(record["path"])
        if relative in (SCHEMA, QUALITY):
            write_new_bytes(root / relative, (stage / relative).read_bytes(), root)
        else:
            destination = check_path(root / relative, root)
            destination.parent.mkdir(parents=True, exist_ok=True)
            with (stage / relative).open("rb") as source, destination.open("xb") as target:
                shutil.copyfileobj(source, target)
        if _record(root, root / relative) != record:
            raise ValueError(f"publication byte mismatch: {relative}")
    request_bytes = (workspace / REQUEST).read_bytes()
    write_new_bytes(workspace / FULFILLED_REQUEST, request_bytes, workspace)
    if root != workspace:
        write_new_bytes(root / FULFILLED_REQUEST, request_bytes, root)
    write_new_bytes(root / MANIFEST, _json(manifest), root)


def build(root, workspace, stage, *, sample, command):
    allowed = workspace / "work/daily-facts-v1"
    stage = check_path(stage, workspace)
    if not stage.is_relative_to(allowed) or stage == allowed:
        raise ValueError("choose a fresh stage inside work/daily-facts-v1")
    check_absent(stage, workspace)
    if not sample:
        _preflight_publication(root, workspace)
    stage.mkdir(parents=True, exist_ok=False)
    sources = publication_sources(Path(__file__), (
        "__init__.py", "daily_facts.py", "daily_facts_loader.py", "daily_facts_verify.py",
        "calendar.py", "continuous_loader.py", "daily_context.py", "manifest_selection.py",
        "paths.py", "publication_safety.py", "provenance.py",
    ), workspace=workspace)
    sources.append((str(REQUEST), workspace / REQUEST))
    provenance = stage / DATA_PATH / "provenance"
    retained = retain_sources(provenance, sources, artifact_id=DATASET_ID, root=workspace)
    inputs = read_inputs(root, workspace)
    days = list(SAMPLE_DAYS) if sample else weekday_roster(START, END)
    tables = {}
    for asset in ASSETS:
        path = stage / DATA_PATH / f"product={asset}/part-000.parquet"
        path.parent.mkdir(parents=True)
        pq.write_table(build_asset(asset, inputs, days), path, compression="zstd")
        tables[asset] = pq.ParquetFile(path).read()
        print(f"{asset}: staged {len(tables[asset]):,} asset sessions", flush=True)
    result = _verify(inputs, tables, days, not sample)
    check_input_records(root, workspace, inputs.records)
    verify_retained_sources(provenance, sources, retained)
    receipt = {**result, "mode": "sample" if sample else "full", "command": command,
               "environment": {"python": sys.version, "numpy": np.__version__, "pyarrow": pa.__version__},
               "code": git_version(workspace), "checked_at_utc": datetime.now(timezone.utc).isoformat()}
    write_new_bytes(provenance / "verification.json", _json(receipt), workspace)
    if sample:
        return receipt

    row_counts = {asset: len(table) for asset, table in tables.items()}
    write_new_bytes(stage / SCHEMA, _json(_schema_contract()), workspace)
    write_new_bytes(stage / QUALITY, _quality_report(result, row_counts,
                                                     sum(map(len, inputs.records.values()))), workspace)
    outputs = [_record(stage, path) for path in sorted((stage / DATA_PATH).rglob("*")) if path.is_file()]
    outputs.extend(_record(stage, stage / relative) for relative in (SCHEMA, QUALITY))
    manifest = {
        "dataset_id": DATASET_ID, "version": VERSION, "definition_version": VERSION,
        "published_at_utc": datetime.now(timezone.utc).isoformat(),
        "start_session_date": str(START), "end_session_date_exclusive": str(END),
        "products": list(ASSETS), "row_counts": row_counts, "input_files": inputs.records,
        "request": {"path": str(FULFILLED_REQUEST), "sha256": PINS[REQUEST]},
        "schema_path": str(SCHEMA), "quality_report": str(QUALITY),
        "verification": str(DATA_PATH / "provenance/verification.json"), "output_files": outputs,
    }
    write_new_bytes(stage / MANIFEST, _json(manifest), workspace)
    _promote(root, workspace, stage, manifest)
    return {"status": "passed", "dataset_id": DATASET_ID, "row_counts": row_counts,
            "manifest": str(root / MANIFEST), "manifest_sha256": sha256_file(root / MANIFEST)}


def verify(root, workspace, manifest_sha256):
    manifest = read_pinned_manifest(root, MANIFEST, manifest_sha256, True)
    if manifest is None:
        raise ValueError("published Daily Facts verification requires an explicit pin")
    selected_files(root, manifest, lambda path: True, verify=True)
    _pin(root, FULFILLED_REQUEST, PINS[REQUEST])
    inputs = read_inputs(root, workspace)
    if manifest["input_files"] != inputs.records:
        raise ValueError("published input inventory differs from the frozen request")
    tables = {asset: load_daily_facts(root, manifest_path=MANIFEST, manifest_sha256=manifest_sha256,
                                    assets=(asset,)) for asset in ASSETS}
    result = _verify(inputs, tables, weekday_roster(START, END), True)
    check_input_records(root, workspace, inputs.records)
    return {**result, "manifest_sha256": manifest_sha256, "verified_outputs": len(manifest["output_files"])}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, help="override the configured publication root")
    actions = parser.add_subparsers(dest="action", required=True)
    for action in ("sample", "build"):
        actions.add_parser(action).add_argument("--stage", type=Path, required=True)
    actions.add_parser("verify").add_argument("--manifest-sha256", required=True)
    args = parser.parse_args()
    workspace = workspace_root()
    root = resolve_publication_root(args.root, workspace=workspace)
    if args.action == "verify":
        result = verify(root, workspace, args.manifest_sha256)
    else:
        command = {"argv": [sys.executable, "-B", "-m", "abacus_bhishma.daily_facts_release",
                            *sys.argv[1:]], "cwd": str(Path.cwd())}
        result = build(root, workspace, args.stage, sample=args.action == "sample", command=command)
    print(_json(result).decode(), end="")


if __name__ == "__main__":
    main()
