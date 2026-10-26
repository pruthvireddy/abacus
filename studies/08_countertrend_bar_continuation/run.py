"""Extract the frozen long-history signal ledger into a new staging directory."""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from src.engine import TICKS, extract_session, iter_sessions, larger_states, verify_inputs


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", required=True, type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    stage = args.stage.resolve()
    if not stage.is_relative_to((root / "work").resolve()) or stage.exists():
        raise ValueError("stage must be a new directory under work/")
    stage.mkdir(parents=True)
    (stage / "tables").mkdir()
    study = Path(__file__).resolve().parent
    lock = json.loads((study / "inputs.lock.json").read_text())
    checked = verify_inputs(root, lock)
    (stage / "inputs.lock.json").write_text(json.dumps(lock, indent=2)+"\n")
    (stage / "config.json").write_text(json.dumps({"protocol":(study / "plan.md").read_text(),
        "study_yaml":(study / "study.yaml").read_text()}, indent=2)+"\n")
    files = {(x["product"],x["setting_ticks"]):x for x in lock["files"] if x["kind"]=="enhanced"}
    larger_pair = {("ES",4):("ES",5), ("ES",5):("ES",6),
                   ("GC",6):("GC",10), ("NQ",10):("NQ",20)}
    audit = {"verified_inputs":checked,"charts":{},"executed_at_utc":datetime.now(timezone.utc).isoformat()}
    for (product,setting), record in files.items():
        key = f"{product}_{setting}"
        print(f"extract {key}", flush=True)
        states = None
        if (product,setting) in larger_pair:
            large = files[larger_pair[(product,setting)]]
            states = larger_states(root / large["path"], TICKS[product])
        writer = None
        sessions = []
        status_counts = Counter()
        last_row = 0
        last_start = ""
        rows = 0
        event_rows = 0
        try:
            for df in iter_sessions(root / record["path"]):
                date = str(df["session_date_proxy"].iloc[0])
                if int(df["source_row"].iloc[0]) != last_row+1:
                    raise ValueError(f"source row discontinuity: {key} {date}")
                if not df["source_row"].is_monotonic_increasing or int(df["source_row"].iloc[-1])-int(df["source_row"].iloc[0])+1 != len(df):
                    raise ValueError(f"source row disorder: {key} {date}")
                if last_start and str(df["bar_start_timestamp"].iloc[0]) < last_start:
                    raise ValueError(f"timestamp regression: {key} {date}")
                if not df["bar_start_timestamp"].is_monotonic_increasing:
                    raise ValueError(f"timestamp regression: {key} {date}")
                last_row = int(df["source_row"].iloc[-1])
                last_start = str(df["bar_start_timestamp"].iloc[-1])
                rows += len(df)
                status_counts.update(df["completion_proxy_status"].value_counts().to_dict())
                events, entry = extract_session(df, product, setting, states.get(date) if states else None)
                sessions.append(entry)
                if len(events):
                    table = pa.Table.from_pandas(events, preserve_index=False)
                    if writer is None:
                        writer = pq.ParquetWriter(stage / "tables" / f"events_{key}.parquet", table.schema,
                                                  compression="zstd")
                    writer.write_table(table)
                    event_rows += len(events)
        finally:
            if writer: writer.close()
        if rows != record["rows"]:
            raise ValueError(f"row count differs: {key}")
        audit["charts"][key] = {"rows":rows,"dates":len(sessions),"events":event_rows,
            "status_counts":dict(status_counts),"sessions":sessions}
        print(f"  {rows:,} bars; {event_rows:,} C1 signals; {len(sessions)} sessions", flush=True)
    (stage / "audit.json").write_text(json.dumps(audit, indent=2)+"\n")
    print(stage, flush=True)


if __name__ == "__main__":
    main()
