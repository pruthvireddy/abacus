"""Create a new C2-confirmation and ordinary-pair staging ledger."""
from __future__ import annotations

import argparse
import json
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
    study = Path(__file__).resolve().parent
    stage = args.stage.resolve()
    if not stage.is_relative_to((root / "work" / study.name).resolve()) or stage.exists():
        raise ValueError("stage must be a new directory under this study's work/")
    lock = json.loads((study / "inputs.lock.json").read_text())
    checked = verify_inputs(root, lock)
    stage.mkdir(parents=True)
    (stage / "tables").mkdir()
    (stage / "inputs.lock.json").write_text(json.dumps(lock, indent=2)+"\n")
    (stage / "config.json").write_text(json.dumps({"plan":(study / "plan.md").read_text(),
        "study_yaml":(study / "study.yaml").read_text()}, indent=2)+"\n")
    manifest = json.loads((root / lock["manifest"]["path"]).read_text())
    expected = {(x["product"],x["setting_ticks"]):x for x in manifest["files"]}
    files = {(x["product"],x["setting_ticks"]):x for x in lock["files"] if x["kind"]=="enhanced"}
    pairs = {("ES",4):("ES",5), ("ES",5):("ES",6),
             ("GC",6):("GC",10), ("NQ",10):("NQ",20)}
    audit = {"executed_at_utc":datetime.now(timezone.utc).isoformat(),
             "verified_inputs":checked,"charts":{}}
    for (product,setting),record in files.items():
        key=f"{product}_{setting}"
        print("extract",key,flush=True)
        larger = None
        if (product,setting) in pairs:
            larger_record=files[pairs[(product,setting)]]
            larger=larger_states(root/larger_record["path"],TICKS[product])
        writers = {"opportunities":None,"ordinary":None}
        counts = Counter()
        sessions = []
        statuses = Counter()
        last_row = 0
        last_start = ""
        try:
            for df in iter_sessions(root/record["path"]):
                date=str(df.session_date_proxy.iloc[0])
                source=df.source_row
                if int(source.iloc[0]) != last_row+1 or not source.is_monotonic_increasing or int(source.iloc[-1])-int(source.iloc[0])+1 != len(df):
                    raise ValueError(f"source row discontinuity: {key} {date}")
                if (last_start and str(df.bar_start_timestamp.iloc[0]) < last_start) or not df.bar_start_timestamp.is_monotonic_increasing:
                    raise ValueError(f"timestamp regression: {key} {date}")
                last_row=int(source.iloc[-1])
                last_start=str(df.bar_start_timestamp.iloc[-1])
                statuses.update(df.completion_proxy_status.value_counts().to_dict())
                opportunities,ordinary,session_audit=extract_session(df,product,setting,
                    larger.get(date) if larger else None)
                sessions.append(session_audit)
                counts["bars"]+=len(df)
                for kind,table in (("opportunities",opportunities),("ordinary",ordinary)):
                    if table.empty:
                        continue
                    batch=pa.Table.from_pandas(table,preserve_index=False)
                    if writers[kind] is None:
                        writers[kind]=pq.ParquetWriter(stage/"tables"/f"{kind}_{key}.parquet",
                            batch.schema,compression="zstd")
                    writers[kind].write_table(batch)
                    counts[kind]+=len(table)
        finally:
            for writer in writers.values():
                if writer is not None:
                    writer.close()
        spec=expected[(product,setting)]
        if counts["bars"] != spec["rows"] or len(sessions) != spec["session_dates_with_data"] or dict(statuses) != spec["completion_proxy_status_counts"]:
            raise ValueError(f"manifest row/session/status mismatch: {key}")
        if counts["opportunities"] != sum(x["c1_signals"] for x in sessions) or counts["ordinary"] != sum(x["ordinary_pairs"] for x in sessions):
            raise ValueError(f"ledger count mismatch: {key}")
        audit["charts"][key]={"bars":counts["bars"],"session_dates":len(sessions),
            "opportunities":counts["opportunities"],"ordinary_pairs":counts["ordinary"],
            "status_counts":dict(statuses),"sessions":sessions}
        print(f"  {counts['bars']:,} bars; {counts['opportunities']:,} C1; {counts['ordinary']:,} ordinary pairs",flush=True)
    (stage/"audit.json").write_text(json.dumps(audit,indent=2)+"\n")
    print(stage,flush=True)


if __name__=="__main__":main()
