"""Independent breach-origin timing audit from canonical saved event rows."""
from __future__ import annotations
import argparse
from collections import defaultdict
import csv
from datetime import datetime, timezone
import gzip
import hashlib
import json
import math
from pathlib import Path
import shutil
import sys


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    with gzip.open(path, "rt") as file:
        return [json.loads(line) for line in file]


def clock(value):
    if value is None:
        return None
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    require(result.tzinfo is not None, "aware event time required")
    return result


def independent_episode(breach, recovery):
    """Interval subtraction, independently expressed in epoch seconds."""
    state = breach["occurred"]
    known = state is True
    require((recovery["breach_occurred"] is True) == known, "canonical breach population disagreement")
    b = clock(breach["first_time"])
    bu = clock(breach["first_time_latest"])
    r = clock(recovery["first_time"])
    ru = clock(recovery["first_time_latest"])
    end = clock(recovery["horizon_end"])
    delay = low = high = None
    if known and recovery["occurred"] is True and all(t is not None for t in (b, bu, r, ru)):
        require(b <= bu and r <= ru and b <= r and bu <= end and ru <= end,
                "event interval chronology")
        delay = (r.timestamp() - b.timestamp()) / 60
        low = max(0., (r.timestamp() - bu.timestamp()) / 60)
        high = max(0., (ru.timestamp() - b.timestamp()) / 60)
        require(low <= delay <= high, "delay must fall within conservative bounds")
    fields = {key: recovery[key] for key in ("episode_id", "broker_day", "year", "session", "side", "horizon", "event")}
    fields.update(level=recovery["recovery_level"], known_breach=known, breach_unknown=state is None,
                  recovered=recovery["occurred"] if known else None,
                  breach_first_time=breach["first_time"], breach_first_time_latest=breach["first_time_latest"],
                  recovery_first_time=recovery["first_time"], recovery_first_time_latest=recovery["first_time_latest"],
                  recovery_confirmation_available_at=recovery["first_available_at"],
                  delay_minutes_source_estimate=delay, delay_minutes_lower=low, delay_minutes_upper=high,
                  post_breach_exposure_minutes_lower=max(0., (end.timestamp()-bu.timestamp())/60) if known and bu is not None else None,
                  post_breach_exposure_minutes_upper=max(0., (end.timestamp()-b.timestamp())/60) if known and b is not None else None,
                  recovery_censored=recovery["occurred"] is None if known else None,
                  horizon_end=recovery["horizon_end"], not_executed_target_or_financial_recovery=True)
    return fields


FIELDS = ("delay_minutes_source_estimate", "delay_minutes_lower", "delay_minutes_upper", "post_breach_exposure_minutes_lower", "post_breach_exposure_minutes_upper")


def independent_groups(rows):
    groups = defaultdict(list)
    for row in rows:
        for year in ("all", row["year"]):
            for session in ("all", row["session"]):
                for side in ("combined", row["side"]):
                    groups[(year, session, side, row["horizon"], row["level"], row["event"])].append(row)
    dimensions = sorted({(r["horizon"], r["level"], r["event"]) for r in rows})
    output = {}
    for year in ("all", *(str(y) for y in range(2018, 2027))):
        for session in ("all", "Asia", "London", "New York", "Outside"):
            for side in ("combined", "upper-first", "lower-first"):
                for horizon, level, event in dimensions:
                    key = (year, session, side, horizon, level, event)
                    selected = groups[key]
                    exposed = [r for r in selected if r["known_breach"]]
                    recovered = [r for r in exposed if r["recovered"] is True]
                    row = dict(zip(("year", "session", "side", "horizon", "level", "event"), key))
                    row.update(original_episodes=len(selected), known_breach_episodes=len(exposed),
                               unknown_breach_episodes=sum(r["breach_unknown"] for r in selected),
                               known_recoveries=len(recovered), known_no_recovery=sum(r["recovered"] is False for r in exposed),
                               unknown_recovery=sum(r["recovered"] is None for r in exposed),
                               unknown_recovery_time=sum(r["delay_minutes_source_estimate"] is None for r in recovered),
                               anchor="original_breakout_fill_cohort; elapsed_origin_first_known_protected_breach",
                               not_executed_target_or_financial_recovery=True)
                    require(row["known_recoveries"] + row["known_no_recovery"] + row["unknown_recovery"] == len(exposed),
                            "breach-risk disposition partition")
                    for field in FIELDS:
                        values = [r[field] for r in exposed if r[field] is not None]
                        row["mean_" + field] = sum(values) / len(values) if values else None
                        row[field + "_denominator"] = len(values)
                    output[key] = row
    return output


def compare(actual, expected, where):
    require(set(actual) == set(expected), where + " exact field schema")
    for key, value in expected.items():
        got = actual[key]
        if value is None:
            require(got in (None, ""), where + ":" + key + " null")
        elif isinstance(value, bool):
            require(got is value or str(got).lower() == str(value).lower(), where + ":" + key + " boolean")
        elif isinstance(value, (float, int)):
            require(got not in (None, "") and math.isclose(float(got), value, rel_tol=1e-10, abs_tol=1e-8), where + ":" + key + " number")
        else:
            require(got == value, where + ":" + key + " value")


def verify(stage):
    folder = stage / "additional/time-recovery"
    freeze = json.loads((folder / "measurement-freeze.json").read_text())
    completion = json.loads((folder / "completion.json").read_text())
    require(freeze["run_id"] == stage.name and freeze["post_policy_execution_declaration"] is True
            and freeze["policy_outputs_masks_or_selection_changed"] is False, "ancillary measurement declaration")
    require(clock(freeze["frozen_at"]) <= clock(completion["finished_at"]), "measurement freeze chronology")
    require(completion["measurement_freeze_sha256"] == sha(folder / "measurement-freeze.json"), "measurement freeze hash")
    paths = ["additional/time-recovery/measurement-freeze.json", "additional/time-recovery/completion.json", "config.json", "selection.json", "environment.lock", freeze["source"]["path"]]
    for name, field in (("config.json", "settings_sha256"), ("selection.json", "selection_sha256"), ("environment.lock", "environment_lock_sha256")):
        require(sha(stage / name) == freeze[field], "measurement control drift")
    require(sha(stage / freeze["source"]["path"]) == freeze["source"]["sha256"], "measurement producer source drift")
    expected_paths = {"phases/" + phase + "/" + kind + ".jsonl.gz" for phase in ("dev-validation", "later") for kind in ("occurrence", "recovery")}
    require({r["path"] for r in freeze["inputs"]} == expected_paths, "canonical four input ledgers")
    occurrence = []; recovery = []
    for pin in freeze["inputs"]:
        path = stage / pin["path"]
        require(path.is_file() and not path.is_symlink() and path.stat().st_size == pin["bytes"] and sha(path) == pin["sha256"], "canonical source byte drift")
        paths.append(pin["path"])
        (occurrence if path.name == "occurrence.jsonl.gz" else recovery).extend(read(path))
    breached = {(r["episode_id"], r["horizon"]): r for r in occurrence if r["event"] == "one_tick_breach"}
    require(len(breached) == 1760, "all880 originals both horizons")
    require(len(recovery) == 10560, "full12 recovery rows per original")
    expected = [independent_episode(breached[(r["episode_id"], r["horizon"])], r) for r in recovery]
    actual = read(folder / "episodes.jsonl.gz")
    require(len(actual) == len(expected) == completion["rows"], "episode roster")
    for index, (got, wanted) in enumerate(zip(actual, expected)):
        compare(got, wanted, "episode:" + str(index))
    groups = independent_groups(expected)
    with (folder / "time-recovery.csv").open(newline="") as handle:
        saved = list(csv.DictReader(handle))
    key_names = ("year", "session", "side", "horizon", "level", "event")
    require(len(saved) == len(groups) == completion["summary_rows"] == 1800, "summary full cohort roster")
    require(len({tuple(r[k] for k in key_names) for r in saved}) == len(saved), "unique summary groups")
    for row in saved:
        key = tuple(row[k] for k in key_names)
        compare(row, groups[key], "summary:" + str(key))
    for pin in completion["artifacts"]:
        path = stage / pin["path"]
        require(path.stat().st_size == pin["bytes"] and sha(path) == pin["sha256"], "measurement output pin")
        paths.append(pin["path"])
    return dict(status="passed", episode_rows=len(expected), summary_rows=len(groups),
                compared_cells=sum(len(r) for r in expected) + sum(len(r) for r in groups.values()),
                method_scope="Requested measurement declared after policy execution; canonical events, orders, masks, selection and existing sixteen tables are unchanged.",
                qualifications=["Source-estimate delay uses saved first minute lower-bound timestamps; conservative bounds preserve within-minute uncertainty.", "Unknown exact first breach/recovery times remain unavailable even where an event was observed.", "Conditional delay means are neither executed profit targets nor survival estimates."],
                artifacts=[dict(path=path, bytes=(stage/path).stat().st_size, sha256=sha(stage/path)) for path in sorted(set(paths))])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", type=Path, required=True)
    parser.add_argument("--attempt", required=True)
    args = parser.parse_args(); stage = args.stage.resolve()
    root = Path(__file__).resolve().parents[2]
    require(stage.is_relative_to(root / "work/23_gc_overnight_breakout_15m"), "new work stage only")
    require(args.attempt.replace("-", "").isalnum(), "new plain attempt name")
    output = stage / "verification" / ("time-recovery-independent-" + args.attempt)
    output.mkdir(parents=True, exist_ok=False)
    snapshots = []
    for source in (Path(__file__), Path(__file__).parent / "tests/test_phase2_time_verifier.py"):
        target = output / source.name; shutil.copyfile(source, target)
        snapshots.append(dict(path=str(target.relative_to(stage)), bytes=target.stat().st_size, sha256=sha(target)))
    receipt = dict(schema_version="study23.phase2-independent-breach-time/v1", command=sys.argv,
                   started_at=datetime.now(timezone.utc).isoformat(), source_snapshots=snapshots)
    try:
        receipt.update(verify(stage))
    except Exception as error:
        receipt.update(status="failed", error=type(error).__name__ + ": " + str(error));raise
    finally:
        receipt["finished_at"] = datetime.now(timezone.utc).isoformat()
        with (output / "receipt.json").open("x") as handle:
            json.dump(receipt, handle, indent=2, allow_nan=False);handle.write("\n")
    print(json.dumps(receipt, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
