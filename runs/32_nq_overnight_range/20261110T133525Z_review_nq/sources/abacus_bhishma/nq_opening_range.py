"""Versioned NQ Daily Facts companion for the overnight and cash windows."""
from __future__ import annotations

import argparse
from bisect import bisect_right
from collections import Counter
from datetime import date, datetime, timezone
from decimal import Decimal
import json
from pathlib import Path
import sys

import numpy as np
import pyarrow as pa
import pyarrow.dataset as ds
import pyarrow.parquet as pq

from .calendar import holiday_sessions
from .continuous_loader import open_continuous_dataset
from .daily_context import load_daily_context
from .daily_facts import (MINUTE_COLUMNS, PRICE, TS, context_facts, measure_window,
                          minute_arrays, minute_groups, weekday_roster, window_bounds)
from .daily_facts_loader import load_daily_facts
from .manifest_selection import read_pinned_manifest, require_identity, selected_files
from .paths import resolve_publication_root, workspace_root
from .provenance import git_version, retain_sources, sha256_file
from .publication_safety import check_absent, write_new_bytes

VERSION = "1.0.0"
ID = f"nq_opening_range_facts__{VERSION}"
MANIFEST = f"catalog/datasets/{ID}.json"
SCHEMA_PATH = f"catalog/schemas/{ID}.json"
DATA = f"data/features/daily/feature_set=nq_opening_range_facts/version={VERSION}/product=NQ/part-000.parquet"
QUALITY = f"reports/quality/{ID}.json"
START = date(2015, 1, 1)
END = date(2026, 9, 19)
OVERLAP = date(2021, 6, 28)
MINUTE_MANIFEST = "catalog/datasets/volume_lead_unadjusted_v1.json"
SCHEDULE = "data/curated/continuous/1m/roll=volume_lead_v1/roll_schedule.parquet"
CONTEXT_MANIFEST = "catalog/datasets/tradingview_daily_context__1.0.0.json"
FACTS_MANIFEST = "catalog/datasets/daily_market_facts__1.0.0.json"
CALENDAR = "catalog/calendars/cme_fixed_clock_session_v1.json"
REQUEST = f"requests/inbox/{ID}.yaml"
PINS = {
    MINUTE_MANIFEST: "00757f5fc8278e75744d7adfaddc688be588d619d82b1dc1811aa60f21b7e5d4",
    SCHEDULE: "0149b99b75da1138454e5face6516184ace3fef819b324183448c678460621b0",
    CONTEXT_MANIFEST: "b7395d6ec2a3263e6f17b2ed95d22ea235d543a01e5b7f850eff81604ba6ce8f",
    FACTS_MANIFEST: "ba5a1b8fb15d7e2ddb4de167122a2930f45868358f66549fb748037c95d60fb2",
    CALENDAR: "d5e9d7895f02c5c66a2231e3f79e6bfbc21cd7ce7aa2f42974cfa50492186bcf",
}
CONTEXT_FIELDS = {
    "close_preopen": pa.float64(), "source_day": pa.date32(), "source_symbol": pa.string(),
    "source_available_at": TS, "age_hours": pa.float64(), "available_at": TS, "status": pa.string(),
}
SCHEMA = pa.schema([
    ("asset", pa.string()), ("session_date", pa.date32()), ("contract_id", pa.uint64()),
    ("contract_symbol", pa.string()), ("roll_id", pa.int16()), ("calendar_status", pa.string()),
    ("calendar_reasons", pa.string()), ("historical_window_qualification", pa.bool_()),
    ("overnight_status", pa.string()), ("rth_status", pa.string()), ("rth_open_status", pa.string()),
    ("overnight_missing_minutes", pa.uint16()), ("rth_missing_minutes", pa.uint16()),
    ("overnight_available_at", TS), ("open_geometry_available_at", TS),
    ("overnight_high", PRICE), ("overnight_low", PRICE), ("overnight_width", PRICE),
    ("overnight_midpoint", pa.decimal128(21, 10)), ("rth_open", PRICE),
    ("distance_to_high", PRICE), ("distance_to_low", PRICE), ("normalized_open", pa.float64()),
    *[(f"{symbol}_{suffix}", kind) for symbol in ("vxn", "vix")
      for suffix, kind in CONTEXT_FIELDS.items()],
])


def opening_geometry(high, low, opening):
    width = None if high is None or low is None else high - low
    usable = width is not None and opening is not None
    return {
        "overnight_high": high, "overnight_low": low, "overnight_width": width,
        "overnight_midpoint": None if width is None else (high + low) / Decimal(2),
        "rth_open": opening, "distance_to_high": high - opening if usable else None,
        "distance_to_low": opening - low if usable else None,
        "normalized_open": float((opening - low) / width) if usable and width > 0 else None,
    }


def load_opening_range(root, *, manifest_sha256):
    manifest = read_pinned_manifest(root, MANIFEST, manifest_sha256, True)
    require_identity(manifest, {"dataset_id": ID, "version": VERSION})
    files = selected_files(root, manifest, lambda path: path == DATA, verify=True)
    if len(files) != 1:
        raise ValueError("expected the single NQ opening range partition")
    table = pq.ParquetFile(files[0]).read()
    if table.schema != SCHEMA or table.num_rows != manifest["rows"]:
        raise ValueError("NQ opening range partition differs from the declared contract")
    return table


def _record(root, relative, expected=None):
    path = root / relative
    digest = sha256_file(path)
    if expected is not None and digest != expected:
        raise ValueError(f"SHA-256 mismatch for {relative}")
    return {"path": str(relative), "bytes": path.stat().st_size, "sha256": digest}


def open_nq_minutes(root):
    return open_continuous_dataset(root, "NQ", manifest_path=MINUTE_MANIFEST,
                                   expected_manifest_sha256=PINS[MINUTE_MANIFEST],
                                   verify_selected_files=True)


def yearly_minutes(dataset, year):
    table = dataset.to_table(columns=list(MINUTE_COLUMNS), filter=ds.field("year") == year)
    return dict(minute_groups(table)), minute_arrays(table.slice(0, 0))


def _independent_complete(arrays, bounds, identity, eligible):
    start, end = (int(value.timestamp()) * 10**9 for value in bounds)
    times = arrays["ts_event"]
    mask = (times >= start) & (times < end)
    return bool(eligible and np.array_equal(times[mask], np.arange(start, end, 60 * 10**9))
                and arrays["valid"][mask].all()
                and (arrays["instrument_id"][mask] == identity[0]).all()
                and (arrays["raw_symbol"][mask] == identity[1]).all()
                and (arrays["roll_id"][mask] == identity[2]).all())


def calculate(root):
    records = [_record(root, path, digest) for path, digest in PINS.items()]
    context_manifest = json.loads((root / CONTEXT_MANIFEST).read_text())
    contexts = {}
    for symbol in ("VXN", "VIX"):
        pin = context_manifest["assets"][symbol]
        records.append(_record(root, pin["output_path"], pin["output_sha256"]))
        source = load_daily_context(root, symbol, version=VERSION,
                                    columns=("trading_day", "available_at", "close")).to_pylist()
        times = [row["available_at"] for row in source]
        if len(times) != pin["published_rows"] or times != sorted(set(times)):
            raise ValueError(f"unexpected {symbol} timestamp ordering")
        contexts[symbol] = (pin["source_symbol"], source, times)
    mappings = sorted((row for row in pq.read_table(root / SCHEDULE).to_pylist() if row["product"] == "NQ"),
                      key=lambda row: row["mapping_start"])
    starts = [row["mapping_start"] for row in mappings]
    if len(starts) != len(set(starts)) or any(left["mapping_end"] != right["mapping_start"]
                                            for left, right in zip(mappings, mappings[1:])):
        raise ValueError("NQ roll mappings must be contiguous and unique")
    dataset = open_nq_minutes(root)
    manifest = json.loads((root / MINUTE_MANIFEST).read_text())
    selected_paths = {str(Path(path).relative_to(root)) for path in dataset.files}
    records.extend(row for row in manifest["output_files"] if row["path"] in selected_paths)
    holidays = holiday_sessions("NQ", START.year, END.year)
    reference = {row["session_date"]: row for row in load_daily_facts(
        root, manifest_path=FACTS_MANIFEST, manifest_sha256=PINS[FACTS_MANIFEST], assets=("NQ",),
    ).to_pylist()}
    facts_release = json.loads((root / FACTS_MANIFEST).read_text())
    records.extend(row for row in facts_release["output_files"]
                   if row["path"].endswith("product=NQ/part-000.parquet"))
    parity_fields = ("overnight_high", "overnight_low", "rth_open", "overnight_status",
                     "rth_status", "rth_open_status", "calendar_status", "overnight_missing_minutes",
                     "rth_missing_minutes")
    rows, coverage = [], Counter()
    checked_overlap = 0
    for year in range(START.year, END.year + 1):
        minutes, empty = yearly_minutes(dataset, year)
        year_start, year_end = date(year, 1, 1), date(year + 1, 1, 1)
        for day in weekday_roster(max(year_start, START), min(year_end, END)):
            index = bisect_right(starts, day) - 1
            if index < 0 or not day < mappings[index]["mapping_end"]:
                raise ValueError(f"no selected contract for {day}")
            mapping = mappings[index]
            identity = mapping["new_instrument_id"], mapping["new_raw_symbol"], mapping["roll_id"]
            reasons = holidays.get(day, [])
            status = "calendar_excluded" if reasons else "eligible"
            bounds = window_bounds("NQ", day)
            arrays = minutes.get(day, empty)
            windows = {}
            for window in ("overnight", "rth"):
                result, _, _ = measure_window(arrays, *bounds[window], identity, status)
                if result["aggregate_ready"] != _independent_complete(
                    arrays, bounds[window], identity, status == "eligible",
                ):
                    raise ValueError(f"independent grid disagrees for {day}/{window}")
                windows[window] = result
            overnight, rth = windows["overnight"], windows["rth"]
            row = {
                "asset": "NQ", "session_date": day, "contract_id": identity[0],
                "contract_symbol": identity[1], "roll_id": identity[2], "calendar_status": status,
                "calendar_reasons": ", ".join(reasons), "historical_window_qualification": day < OVERLAP,
                "overnight_status": overnight["status"], "rth_status": rth["status"],
                "rth_open_status": rth["open_status"], "overnight_missing_minutes": overnight["missing_minutes"],
                "rth_missing_minutes": rth["missing_minutes"], "overnight_available_at": overnight["end"],
                "open_geometry_available_at": rth["open_available_at"],
                **opening_geometry(overnight["high"], overnight["low"], rth["open"]),
            }
            for symbol, (source_symbol, source, times) in contexts.items():
                cutoff = rth["start"]
                selected = bisect_right(times, cutoff) - 1
                context = context_facts(source[selected] if selected >= 0 else None,
                                        symbol, source_symbol, cutoff, status)
                row.update({f"{symbol.lower()}_{suffix}": context[f"vol_index_{suffix}"]
                            for suffix in CONTEXT_FIELDS})
            if day >= OVERLAP:
                previous = reference[day]
                if (any(row[key] != previous[key] for key in parity_fields)
                        or row["overnight_width"] != previous["overnight_range_points"]
                        or row["contract_id"] != previous["source_contract_id"]
                        or any(row[f"vxn_{suffix}"] != previous[f"vol_index_{suffix}"]
                               for suffix in CONTEXT_FIELDS)):
                    raise ValueError(f"Daily Facts overlap parity failed for {day}")
                checked_overlap += 1
            rows.append(row)
            coverage[(year, "roster")] += 1
            coverage[(year, "eligible")] += int(status == "eligible")
            coverage[(year, "overnight_complete")] += int(overnight["aggregate_ready"])
            coverage[(year, "rth_complete")] += int(rth["aggregate_ready"])
            coverage[(year, "both_complete")] += int(overnight["aggregate_ready"] and rth["aggregate_ready"])
    if checked_overlap != len(reference):
        raise ValueError("incomplete Daily Facts overlap")
    quality = {
        "independent_window_grid_comparisons": 2 * len(rows), "daily_facts_overlap_rows": checked_overlap,
        "annual_coverage": [{"year": year, **{name: count for (key, name), count in coverage.items()
                                               if key == year}} for year in range(START.year, END.year + 1)],
    }
    return pa.Table.from_pylist(rows, schema=SCHEMA), quality, records


def _json(value):
    return (json.dumps(value, indent=2, allow_nan=False) + "\n").encode()


def publish(root, workspace, stage):
    for relative in (MANIFEST, SCHEMA_PATH, DATA, QUALITY):
        check_absent(root / relative, root)
    check_absent(stage, workspace)
    stage.mkdir(parents=True, exist_ok=False)
    table, quality, records = calculate(root)
    parquet = stage / "part-000.parquet"
    pq.write_table(table, parquet, compression="zstd")
    if not pq.ParquetFile(parquet).read().equals(table):
        raise ValueError("portable release readback differs")
    schema = _json({"dataset_id": ID, "primary_key": ["asset", "session_date"],
                    "fields": [{"name": field.name, "type": str(field.type)} for field in SCHEMA],
                    "price_units": "NQ points", "range_availability": "09:30 ET",
                    "opening_geometry_availability": "09:31 ET"})
    paths = [Path(__file__).resolve(), *[Path(__file__).with_name(name + ".py") for name in (
        "calendar", "continuous_loader", "daily_context", "daily_facts", "daily_facts_loader",
        "manifest_selection", "paths", "provenance", "publication_safety")],
        workspace / "uv.lock", workspace / REQUEST]
    retained = retain_sources(stage / "sources", [(path.name, path) for path in paths],
                              artifact_id=ID, root=workspace)
    quality_bytes = _json(quality)
    payloads = {DATA: parquet.read_bytes(), SCHEMA_PATH: schema, QUALITY: quality_bytes}
    for relative, payload in payloads.items():
        write_new_bytes(root / relative, payload, root)
    manifest = {
        "dataset_id": ID, "version": VERSION, "rows": len(table),
        "published_at_utc": datetime.now(timezone.utc).isoformat(),
        "start": START.isoformat(), "end_exclusive": END.isoformat(),
        "input_files": records, "request": _record(workspace, REQUEST), "producer": retained,
        "code": git_version(workspace), "command": [sys.executable, *sys.argv],
        "output_files": [_record(root, relative) for relative in payloads],
    }
    write_new_bytes(root / MANIFEST, _json(manifest), root)
    print(sha256_file(root / MANIFEST), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", required=True, type=Path)
    args = parser.parse_args()
    workspace = workspace_root()
    publish(resolve_publication_root(workspace=workspace), workspace, args.stage.resolve())


if __name__ == "__main__":
    main()
