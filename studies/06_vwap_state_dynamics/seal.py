"""Seal the verified, self-identifying study 06 evidence exactly once."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import shutil
import subprocess

import pyarrow.parquet as pq

from src.features import digest


def command(args, cwd):
    return subprocess.check_output(args,cwd=cwd,text=True).strip()


def parquet_manifest(stage: Path, folder: str) -> dict:
    parts=[]
    for path in sorted((stage/folder).glob("*.parquet")):
        file=pq.ParquetFile(path)
        parts.append({"path":str(path.relative_to(stage)),"rows":file.metadata.num_rows,
                      "bytes":path.stat().st_size,"sha256":digest(path)})
    first=pq.read_schema(stage/parts[0]["path"])
    return {"location":folder+"/","format":"Parquet","retention":"included_in_sealed_run",
            "row_count":sum(x["rows"] for x in parts),"partitions":parts,
            "schema":{field.name:str(field.type) for field in first}}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--run-id",required=True)
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[2]
    study=root/"studies/06_vwap_state_dynamics"
    stage=root/"work/06_vwap_state_dynamics"/args.run_id
    dest=root/"runs/06_vwap_state_dynamics"/args.run_id
    if not stage.is_dir() or dest.exists():
        raise FileNotFoundError("stage missing or sealed destination already exists")
    result=json.loads((stage/"verification-results.json").read_text())
    if result.get("status")!="passed" or result.get("event_rows")!=367719:
        raise ValueError("verification has not passed")
    events=parquet_manifest(stage,"events")
    features=parquet_manifest(stage,"features")
    if events["row_count"]!=367719 or features["row_count"]!=367719:
        raise ValueError("partition manifest count mismatch")
    (stage/"events.manifest.json").write_text(json.dumps(events,indent=2)+"\n")
    (stage/"features.manifest.json").write_text(json.dumps(features,indent=2)+"\n")
    snapshot=stage/"source-snapshot"
    if snapshot.exists():raise FileExistsError(snapshot)
    snapshot.mkdir()
    names=("plan.md","README.md","notes.md","study.json","study.yaml","inputs.lock.json",
           "protocol-1.0.0.json","protocol-1.0.0.md","pilot.py","join_audit.py","run.py",
           "summarize.py","audit.py","render.py","verify.py","seal.py")
    for name in names:
        shutil.copy2(study/name,snapshot/name)
    for folder in ("src","tests"):
        shutil.copytree(study/folder,snapshot/folder,ignore=shutil.ignore_patterns("__pycache__","*.pyc"))
    revision=command(["git","rev-parse","HEAD"],root)
    status=command(["git","status","--short"],root)
    (stage/"git-status.txt").write_text(status+"\n")
    exact=[
        f".venv/bin/python studies/06_vwap_state_dynamics/pilot.py --run-id {args.run_id}",
        f".venv/bin/python studies/06_vwap_state_dynamics/join_audit.py --run-id {args.run_id}",
        f".venv/bin/python studies/06_vwap_state_dynamics/run.py --run-id {args.run_id} --workers 3",
        f".venv/bin/python studies/06_vwap_state_dynamics/summarize.py --run-id {args.run_id}",
        f".venv/bin/python studies/06_vwap_state_dynamics/audit.py --run-id {args.run_id}",
        f".venv/bin/python studies/06_vwap_state_dynamics/render.py --run-id {args.run_id}",
        f".venv/bin/python studies/06_vwap_state_dynamics/verify.py --run-id {args.run_id}",
        f".venv/bin/python studies/06_vwap_state_dynamics/seal.py --run-id {args.run_id}"]
    checks={"status":"passed_before_seal","verification":"verification-results.json",
            "focused_tests":"focused-tests.log","numerical_audit":"numerical-audit.json",
            "input_identity":"input-verification.json","source_key_join":"feature-source-key-audit.json",
            "denominator_and_event_reconciliation":"tables/funnel.csv and metrics.json",
            "report_link_and_svg_validation":"verification-results.json"}
    (stage/"checks.json").write_text(json.dumps(checks,indent=2)+"\n")
    artifacts=[]
    for path in sorted(stage.rglob("*")):
        if path.is_file() and path.name!="manifest.json":
            artifacts.append({"path":str(path.relative_to(stage)),"bytes":path.stat().st_size,
                              "sha256":digest(path)})
    manifest={"schema_version":1,"study_id":"06_vwap_state_dynamics","run_id":args.run_id,
              "sealed_at_utc":datetime.now(timezone.utc).isoformat(),"protocol_version":"1.0.0",
              "protocol_sha256":digest(stage/"protocol-1.0.0.json"),
              "template_version":"2026-09-23","git_revision":revision,
              "git_status_at_seal":"git-status.txt","source_snapshot":"source-snapshot/",
              "environment":{"python":platform.python_version(),"platform":platform.platform(),
                             "dependency_lock_sha256":digest(root/"uv.lock")},
              "release_id":"session_anchored_vwap__1.0.0",
              "bootstrap":{"unit":"shared_calendar_date","seed":606,"repetitions":400},
              "exact_commands":exact,"staged_revisions":["summarize.py rerun for context denominators and baseline columns",
                                                  "render.py rerun for text fidelity; no event change"],
              "abandoned_feature_only_pilots":["20260923T180000Z_state06","20260923T180000Z_state06b"],
              "checks":"checks.json","inputs":"input-verification.json",
              "event_evidence":"events.manifest.json","feature_evidence":"features.manifest.json",
              "artifact_hashes":artifacts}
    (stage/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
    dest.parent.mkdir(parents=True,exist_ok=True)
    stage.rename(dest)
    print(dest)


if __name__=="__main__":main()
