"""Reconcile the saved ledgers, manifest audit, and selected original CSV rows."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import pandas as pd


TRACES = {"ES_5": [55, 1250, 1654]}


def source_rows(path: Path, wanted: set[int]) -> dict[int, list[str]]:
    out = {}
    with path.open(newline="") as f:
        for number, row in enumerate(csv.reader(f, delimiter=";"), 1):
            if number in wanted:
                out[number] = row
            if len(out) == len(wanted):
                break
    if set(out) != wanted:
        raise AssertionError("source trace rows missing")
    return out


def enhanced_rows(path: Path, wanted: set[int]) -> dict[int, dict]:
    out = {}
    with path.open(newline="") as f:
        for row in csv.DictReader(f, delimiter=";"):
            number = int(row["source_row"])
            if number in wanted:
                out[number] = row
            if len(out) == len(wanted):
                break
    if set(out) != wanted:
        raise AssertionError("enhanced trace rows missing")
    return out


def direction(row: dict) -> int:
    return (float(row["close"]) > float(row["open"])) - (float(row["close"]) < float(row["open"]))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", required=True, type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    stage = args.stage.resolve()
    audit = json.loads((stage / "audit.json").read_text())
    lock = json.loads((stage / "inputs.lock.json").read_text())
    manifest = json.loads((root / lock["manifest"]["path"]).read_text())
    checked = {x["path"]: x["sha256"] for x in audit["verified_inputs"]}
    assert checked[lock["manifest"]["path"]] == lock["manifest"]["sha256"]
    files = {(x["product"], x["setting_ticks"]): x for x in manifest["files"]}
    trace_records = []
    chart_quality = {}
    all_dates = {}
    overall = pd.read_csv(stage / "tables" / "overall.csv")
    lookup = pd.read_csv(stage / "tables" / "lookup.csv")
    run_lengths = pd.read_csv(stage / "tables" / "run_lengths.csv")
    for key, info in audit["charts"].items():
        product, setting = key.split("_")
        setting = int(setting)
        record = files[(product, setting)]
        assert checked[record["source_path"]] == record["source_sha256"]
        assert checked[record["enhanced_path"]] == record["enhanced_sha256"]
        assert info["rows"] == record["rows"]
        assert info["dates"] == record["session_dates_with_data"]
        assert info["status_counts"] == record["completion_proxy_status_counts"]
        sessions = info["sessions"]
        dates = [x["date"] for x in sessions]
        assert dates == sorted(set(dates))
        assert sum(x["bars"] for x in sessions) == info["rows"]
        all_dates[key] = set(dates)
        events = pd.read_parquet(stage / "tables" / f"events_{key}.parquet")
        assert len(events) == info["events"] == sum(x["signals"] for x in sessions)
        assert (events.c2_c3_follow <= events.c2_follows).all()
        assert (events.c2_c3_c4_follow <= events.c2_c3_follow).all()
        assert not events.loc[events.primary_eligible, "c1_same_second"].any()
        paired = events.loc[events.larger_context.ne("unavailable")]
        if len(paired):
            assert (pd.to_datetime(paired.larger_completion) < pd.to_datetime(paired.c1_completion)).all()
        primary = events.loc[events.primary_eligible & ~events.gc_gap_excluded]
        assert not primary.gc_gap_excluded.any()
        for direction_value, cohort in primary.groupby("direction"):
            expected = overall.loc[(overall["product"] == product) & (overall.setting == setting) &
                                   (overall.direction == direction_value)]
            for metric, numerator in [("p1", int(cohort.c2_follows.sum())),
                                      ("p2", int(cohort.c2_c3_follow.sum())),
                                      ("immediate_resumption", int(cohort.immediate_resumption.sum()))]:
                row = expected.loc[expected.metric == metric].iloc[0]
                assert (int(row.numerator), int(row.denominator)) == (numerator, len(cohort))
            p2_lookup = lookup.loc[(lookup["product"] == product) & (lookup.setting == setting) &
                                   (lookup.direction == direction_value) & (lookup.metric == "p2")]
            assert int(p2_lookup.denominator.sum()) == len(cohort)
            assert int(p2_lookup.numerator.sum()) == int(cohort.c2_c3_follow.sum())
            dist = run_lengths.loc[(run_lengths["product"] == product) &
                                   (run_lengths.setting == setting) & (run_lengths.direction == direction_value)]
            assert int(dist.numerator.sum()) == len(cohort)
        chart_quality[key] = {"rows": info["rows"], "session_dates": info["dates"],
                              "signals": len(events), "eligible_primary": len(primary),
                              "signal_completion_excluded": sum(x.get("signal_completion_excluded", 0) for x in sessions),
                              "horizon_or_completion_excluded": sum(x.get("horizon_or_completion_excluded", 0) for x in sessions),
                              "same_second_signals": sum(x.get("same_second_signals", 0) for x in sessions),
                              "larger_equal_second_ties": sum(x.get("larger_equal_second_ties", 0) for x in sessions)}
        if key in TRACES:
            targets = events.loc[events.source_row.isin(TRACES[key])]
            assert len(targets) == len(TRACES[key])
            wanted = set()
            for _, event in targets.iterrows():
                wanted.update(range(int(event.source_row - event.prior_run), int(event.source_row + 4)))
            raw = source_rows(root / record["source_path"], wanted)
            enhanced = enhanced_rows(root / record["enhanced_path"], wanted)
            for _, event in targets.iterrows():
                row_id = int(event.source_row)
                preceding = [direction(enhanced[j]) for j in range(row_id-int(event.prior_run), row_id)]
                after = [direction(enhanced[j]) for j in range(row_id, row_id+3)]
                assert len(set(preceding)) == 1 and preceding[0] == -int(event.direction)
                assert after[0] == int(event.direction)
                assert bool(after[1] == after[0]) == bool(event.c2_follows)
                assert bool(after[2] == after[0]) == bool(event.c3_follows)
                for j in range(row_id-int(event.prior_run), row_id+3):
                    assert raw[j] == [enhanced[j]["source_timestamp"], enhanced[j]["open"],
                                      enhanced[j]["high"], enhanced[j]["low"], enhanced[j]["close"]]
                trace_records.append({"chart": key, "session_date": event.session_date,
                    "c1_source_row": row_id, "prior_source_rows": f"{row_id-int(event.prior_run)}-{row_id-1}",
                    "c2_source_row": row_id+1, "c3_source_row": row_id+2,
                    "directions_prior_c1_c2_c3": f"{preceding[0]}x{len(preceding)},{after[0]},{after[1]},{after[2]}",
                    "two_more_success": bool(event.c2_c3_follow),
                    "c1_completion_wall_time": event.c1_completion,
                    "larger_completion_wall_time": event.larger_completion,
                    "larger_equal_second_tie": bool(event.larger_equal_second_tie)})
    missing_gc = {key: sorted(all_dates["ES_5"] - dates) for key, dates in all_dates.items() if key.startswith("GC_")}
    pd.DataFrame(trace_records).to_csv(stage / "tables" / "real_event_traces.csv", index=False)
    checks = {"status": "pass", "manifest_sha256": lock["manifest"]["sha256"],
              "charts": chart_quality, "gc_dates_absent_relative_to_es": missing_gc,
              "trace_count": len(trace_records),
              "checks": ["manifest hashes and row/status/date counts", "session and source row continuity",
                         "signal/outcome ledger and denominator arithmetic", "strict larger completion ordering",
                         "run-length distribution totals", "manual source/enhanced row traces"]}
    (stage / "checks.json").write_text(json.dumps(checks, indent=2) + "\n")
    print(json.dumps({"status": checks["status"], "charts": len(chart_quality),
                      "traces": len(trace_records), "gc_absent_dates": missing_gc}, indent=2))


if __name__ == "__main__":
    main()
