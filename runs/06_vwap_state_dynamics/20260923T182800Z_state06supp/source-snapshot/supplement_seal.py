"""Seal the exploratory reporting supplement without editing its parent run."""

from __future__ import annotations

import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import platform
import shutil
import subprocess

from src.features import digest


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--run-id",required=True);args=parser.parse_args()
    root=Path(__file__).resolve().parents[2]
    study=root/"studies/06_vwap_state_dynamics"
    stage=root/"work/06_vwap_state_dynamics"/args.run_id
    dest=root/"runs/06_vwap_state_dynamics"/args.run_id
    if not stage.is_dir() or dest.exists():
        raise FileNotFoundError("stage missing or destination already sealed")
    verification=json.loads((stage/"verification-results.json").read_text())
    if verification.get("status")!="passed" or verification.get("primary_landmarks_clock_partitioned")!=133716:
        raise ValueError("supplement verification incomplete")
    snapshot=stage/"source-snapshot"
    snapshot.mkdir()
    names=("plan.md","README.md","notes.md","study.json","study.yaml","inputs.lock.json",
           "protocol-1.0.0.json","protocol-1.0.0.md","protocol-1.1.0.json","protocol-1.1.0.md",
           "pilot.py","join_audit.py","run.py","summarize.py","audit.py","render.py","verify.py","seal.py",
           "supplement.py","supplement_verify.py","supplement_seal.py")
    for name in names:
        shutil.copy2(study/name,snapshot/name)
    for folder in ("src","tests"):
        shutil.copytree(study/folder,snapshot/folder,ignore=shutil.ignore_patterns("__pycache__","*.pyc"))
    revision=subprocess.check_output(["git","rev-parse","HEAD"],cwd=root,text=True).strip()
    status=subprocess.check_output(["git","status","--short"],cwd=root,text=True).strip()
    (stage/"git-status.txt").write_text(status+"\n")
    (stage/"checks.json").write_text(json.dumps({"status":"passed_before_seal",
        "parent_hashes":"parent-verification.json","numerical_denominators":"verification-results.json",
        "focused_tests":"focused-tests.log","report_links":"verification-results.json"},indent=2)+"\n")
    artifacts=[]
    for path in sorted(stage.rglob("*")):
        if path.is_file() and path.name!="manifest.json":
            artifacts.append({"path":str(path.relative_to(stage)),"bytes":path.stat().st_size,
                              "sha256":digest(path)})
    parent=root/"runs/06_vwap_state_dynamics/20260923T180000Z_state06c"
    manifest={"schema_version":1,"study_id":"06_vwap_state_dynamics","run_id":args.run_id,
        "sealed_at_utc":datetime.now(timezone.utc).isoformat(),
        "protocol_version":"1.1.0","exploratory_after_primary_outcomes_viewed":True,
        "parent_run_id":"20260923T180000Z_state06c",
        "parent_manifest_sha256":digest(parent/"manifest.json"),
        "protocol_sha256":digest(stage/"protocol-1.1.0.json"),
        "template_version":"2026-09-23","git_revision":revision,"git_status_at_seal":"git-status.txt",
        "source_snapshot":"source-snapshot/",
        "environment":{"python":platform.python_version(),"platform":platform.platform(),
                       "dependency_lock_sha256":digest(root/"uv.lock")},
        "release_id":"session_anchored_vwap__1.0.0",
        "event_evidence":"events.manifest.json","inputs":"input-verification.json",
        "bootstrap":{"unit":"shared_calendar_date","seed":607,"repetitions":400},
        "exact_commands":[
            f".venv/bin/python studies/06_vwap_state_dynamics/supplement.py --run-id {args.run_id}",
            f".venv/bin/python studies/06_vwap_state_dynamics/supplement_verify.py --run-id {args.run_id}",
            f".venv/bin/python studies/06_vwap_state_dynamics/supplement_seal.py --run-id {args.run_id}"],
        "staged_revision":"HTML supplemental section moved before footer; no numerical changes",
        "checks":"checks.json","artifact_hashes":artifacts}
    (stage/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
    dest.parent.mkdir(parents=True,exist_ok=True)
    stage.rename(dest)
    print(dest)


if __name__=="__main__":main()
