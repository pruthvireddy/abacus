"""Bind passing independent attempts into fresh canonical Phase2 receipts.

This metadata-only step rechecks retained local bytes, preserves every prior
attempt, and creates no new research calculation or publication.
"""
from __future__ import annotations
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import sys


def digest(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda:handle.read(1024*1024),b""):h.update(block)
    return h.hexdigest()


def pin(stage,relative):
    path=stage/relative
    if Path(relative).is_absolute() or ".." in Path(relative).parts or not path.is_file() or path.is_symlink():
        raise ValueError("ordinary stage-relative evidence required")
    return dict(path=relative,bytes=path.stat().st_size,sha256=digest(path))


def validate(stage,receipt):
    if receipt.get("status")!="passed":raise ValueError("passing independent attempt required")
    for record in [*receipt["artifacts"],*receipt.get("source_snapshots",[])]:
        if pin(stage,record["path"])!=record:raise ValueError("verified evidence bytes changed")


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage",required=True,type=Path)
    parser.add_argument("--science-attempt",required=True)
    parser.add_argument("--time-attempt",required=True)
    args=parser.parse_args();stage=args.stage.resolve()
    root=Path(__file__).resolve().parents[2]
    if not stage.is_relative_to(root/"work/23_gc_overnight_breakout_15m") or (root/"runs/23_gc_overnight_breakout_15m"/stage.name).exists():
        raise ValueError("owning unsealed stage only")
    names=("scientific-verification.json","metrics-verification.json","account-verification.json","time-recovery-verification.json")
    if any((stage/name).exists() for name in names):raise FileExistsError("canonical receipts are never overwritten")
    science_path=args.science_attempt;time_path=args.time_attempt
    science=json.loads((stage/science_path).read_text());timing=json.loads((stage/time_path).read_text())
    validate(stage,science);validate(stage,timing)
    if science["phase"]!="all" or science["baseline_accepted_episodes"]!=880 or len(science["phases"])!=2:
        raise ValueError("all-phase scientific verification required")
    first_path="verification/original-first-side-audit.json"
    first=json.loads((stage/first_path).read_text())
    first_source=Path(__file__).parent/"phase2_first_side_audit.py"
    if first["status"]!="passed" or first["checker_sha256"]!=digest(first_source):raise ValueError("first-side audit source mismatch")
    folder=stage/"verification/canonical-receipts"
    folder.mkdir(parents=True,exist_ok=False)
    snapshots=[]
    for source in (Path(__file__),first_source):
        target=folder/source.name;shutil.copyfile(source,target)
        snapshots.append(pin(stage,str(target.relative_to(stage))))
    for name,scope in zip(names[:3],("All accepted-episode causal signal/execution/event reconstruction, sensitivity paths and source examples.","All sixteen declared saved tables, aggregate/interval/selection/cohort/transition arithmetic.","Actual source-account whole-quantity constraints, causal eligibility, unknown-equity/fill/loss propagation and saved account/capacity cohorts.")):
        record=deepcopy(science)
        record["canonical_scope"]=scope
        record["canonicalized_at"]=datetime.now(timezone.utc).isoformat()
        record["canonicalization_command"]=sys.argv
        record["independent_attempt_receipt"]=pin(stage,science_path)
        record["artifacts"].extend([pin(stage,science_path),pin(stage,first_path)])
        record["source_snapshots"].extend(snapshots)
        record["first_side_audit"]={k:first[k] for k in ("original_episodes","both_range_boundaries_visited_in_fill_minute","inside_open_unresolved_first_side","baseline_ambiguous_flags","interpretation")}
        record["limits"].append("Raw gap_entry metadata preserves exact raw-price/reference float inequality and can reflect binary price noise; it is never interpreted as a one-tick gap. Independent fill and stop decisions remain tick tolerant.")
        if name=="scientific-verification.json":
            record["additional_requested_measurement"]=pin(stage,time_path)
            record["artifacts"].append(pin(stage,time_path))
        with (stage/name).open("x") as handle:json.dump(record,handle,indent=2,allow_nan=False);handle.write("\n")
    timing=deepcopy(timing)
    timing["independent_attempt_receipt"]=pin(stage,time_path)
    timing["artifacts"].append(pin(stage,time_path))
    timing["source_snapshots"].append(snapshots[0])
    timing["canonicalization_command"]=sys.argv
    with (stage/names[3]).open("x") as handle:json.dump(timing,handle,indent=2,allow_nan=False);handle.write("\n")
    print(json.dumps(dict(status="passed",canonical_receipts=[pin(stage,name) for name in names]),indent=2))


if __name__=="__main__":main()
