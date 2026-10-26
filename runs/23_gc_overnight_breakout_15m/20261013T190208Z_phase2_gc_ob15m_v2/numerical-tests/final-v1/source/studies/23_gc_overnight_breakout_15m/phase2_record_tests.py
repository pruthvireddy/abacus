"""Record one fresh stage-bound Phase 2 numerical unittest execution.

Uses the existing locked environment without sync and the existing unittest_child
actual TestResult. It snapshots current study Python/tests and the child/uv
wrappers before execution, then rejects byte drift and nonpassing results.
No historical market calculation or sealing occurs here.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys

from phase2_seal import (HERE,ROOT,STUDY,RUNTIME,digest,identity,ordinary,pin,
                         read_json,relative,write_new)

SCHEMA="study23.phase2-numerical-record/v1"
ENVIRONMENT_KEYS=("PATH","PYTHONPATH","UV_CACHE_DIR","UV_PROJECT_ENVIRONMENT","VIRTUAL_ENV","PYTHONDONTWRITEBYTECODE")


def _frozen(stage,root):
    stage=ordinary(stage,directory=True);root=ordinary(root,directory=True)
    if stage.parent!=root/"work"/STUDY:raise ValueError("direct owning new work stage required")
    config=read_json(stage/"config.json");freeze=read_json(stage/"execution-freeze.json")
    if config.get("run_id")!=stage.name or config.get("protocol_version")!="2.0.0":raise ValueError("numeric record belongs to another phase/run")
    for name,key in (("config.json","settings_sha256"),("protocol.md","protocol_sha256"),("inputs.lock.json","inputs_sha256"),("phase2-baseline-pin.json","baseline_pin_sha256"),("environment.lock","environment_lock_sha256")):
        pin(stage,{"path":name,"sha256":freeze[key]})
    if digest(ordinary(root/"uv.lock"))!=freeze["environment_lock_sha256"]:raise ValueError("workspace lock differs from executed stage")
    prefix="source/studies/"+STUDY+"/"
    source_by_name={item["path"][len(prefix):]:item for item in freeze["source_files"] if item["path"].startswith(prefix)}
    if not RUNTIME<=set(source_by_name):raise ValueError("complete executed runtime pins required")
    for name in RUNTIME:
        item=source_by_name[name];pin(stage,item)
        pin(root,{"path":"studies/"+STUDY+"/"+name,"bytes":item["bytes"],"sha256":item["sha256"]})
    return stage,root,freeze


def _meaningful(result):
    if result.get("outcome")!="passed":raise ValueError("actual child unittest outcome did not pass")
    counts=result.get("counts",{})
    for key in ("discovered","tests_run","failures","errors","skipped","expected_failures","unexpected_successes"):
        if type(counts.get(key)) is not int or counts[key]<0:raise ValueError("invalid actual TestResult count")
    if counts["tests_run"]!=counts["discovered"] or counts["tests_run"]<=counts["skipped"] or any(counts[k] for k in ("failures","errors","unexpected_successes")):
        raise ValueError("actual numerical discovery/results were empty, skipped or nonpassing")
    if type(result.get("successful_callbacks")) is not int or result["successful_callbacks"]<=0:raise ValueError("actual successful test callbacks required")


def validate_record(stage,record,root=ROOT):
    """Read-only source/TestResult drift guard for a previously saved record."""
    stage,root,freeze=_frozen(stage,root)
    receipt=read_json(ordinary(record)) if isinstance(record,(str,Path)) else record
    if receipt.get("schema_version")!=SCHEMA or receipt.get("status")!="passed" or receipt.get("run_id")!=stage.name:
        raise ValueError("required passed stage-bound numeric record absent")
    for name,key in (("config.json","settings_sha256"),("execution-freeze.json","execution_freeze_sha256"),("environment.lock","environment_lock_sha256")):
        if digest(stage/name)!=receipt[key]:raise ValueError("numeric record stage binding changed")
    for item in receipt["artifacts"]:pin(stage,item)
    child=read_json(pin(stage,receipt["child_result"]))
    _meaningful(child)
    for field in ("counts","successful_callbacks","skips"):
        if receipt[field]!=child[field]:raise ValueError("receipt cannot replace actual child TestResult fields")
    if receipt["child_outcome"]!=child["outcome"]:raise ValueError("actual child outcome mismatch")
    if not receipt.get("source_snapshots"):raise ValueError("numeric source snapshots absent")
    for item in receipt["source_snapshots"]:
        pin(stage,item)
        pin(root,{"path":item["original_workspace_path"],"bytes":item["bytes"],"sha256":item["sha256"]})
    if "--locked" not in receipt["command"] or "--no-sync" not in receipt["command"]:raise ValueError("numeric execution must use locked no-sync environment")
    return receipt


def record_tests(stage,*,root=ROOT,attempt="final"):
    stage,root,freeze=_frozen(stage,root)
    ordinary(root/"runs"/STUDY/stage.name,absent=True)
    ordinary(stage/"sealed-bundle",absent=True)
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*",attempt):raise ValueError("plain fresh numerical attempt required")
    folder=ordinary(stage/"numerical-tests"/attempt,absent=True)
    study=ordinary(root/"studies"/STUDY,directory=True)
    if any(p.is_symlink() for p in study.rglob("*")):raise ValueError("symlink study/test selection refused")
    current=sorted(study.rglob("*.py"))
    for item in current:ordinary(item)
    wrappers=[ordinary(root/"scripts/unittest_child.py"),ordinary(root/"scripts/uv")]
    if not current or not any(p.parent.name=="tests" for p in current):raise ValueError("actual study/test source selection absent")
    stage_pins=[identity(stage,name) for name in ("config.json","execution-freeze.json","environment.lock","protocol.md","inputs.lock.json","phase2-baseline-pin.json")]
    execution_freeze_sha=stage_pins[1]["sha256"]
    folder.mkdir(parents=True,exist_ok=False)
    snapshots=[]
    for source in [*current,*wrappers]:
        original=str(source.relative_to(root));copy=folder/"source"/original
        copy.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,copy)
        snapshots.append({**identity(stage,str(copy.relative_to(stage))),"original_workspace_path":original})
    result_path=folder/"child-result.json";log_path=folder/"tests.log"
    selection={"start_dir":str(study/"tests"),"pattern":"test*.py"}
    command=[str(root/"scripts/uv"),"run","--locked","--no-sync","python",str(root/"scripts/unittest_child.py"),"--spec",json.dumps(selection,separators=(",",":")),"--result",str(result_path)]
    environment=dict(os.environ);environment["PYTHONDONTWRITEBYTECODE"]="1"
    observed_environment={key:environment[key] for key in ENVIRONMENT_KEYS if key in environment}
    started=datetime.now(timezone.utc).isoformat()
    error=None;child={};returncode=None
    try:
        run=subprocess.run(command,cwd=root,env=environment,text=True,capture_output=True)
        returncode=run.returncode
        with log_path.open("x",encoding="utf-8") as stream:stream.write(run.stdout+run.stderr)
        child=read_json(ordinary(result_path))
        if returncode!=0:raise ValueError("actual child exit code: "+str(returncode))
        _meaningful(child)
        _frozen(stage,root)
        for item in stage_pins:pin(stage,item)
        for item in snapshots:
            pin(stage,item)
            pin(root,{"path":item["original_workspace_path"],"bytes":item["bytes"],"sha256":item["sha256"]})
    except (ValueError,OSError,KeyError,TypeError,AttributeError) as failure:
        error=type(failure).__name__+": "+str(failure)
        if not log_path.exists():
            with log_path.open("x",encoding="utf-8") as stream:stream.write(error+"\n")
    artifacts=[identity(stage,str(path.relative_to(stage))) for path in (log_path,result_path) if path.is_file()]
    receipt={"schema_version":SCHEMA,"status":"failed" if error else "passed","run_id":stage.name,"attempt":attempt,
        "started_at":started,"finished_at":datetime.now(timezone.utc).isoformat(),"command":command,"cwd":str(root),
        "environment":observed_environment,"selection":selection,"returncode":returncode,
        "settings_sha256":freeze["settings_sha256"],"execution_freeze_sha256":execution_freeze_sha,
        "environment_lock_sha256":freeze["environment_lock_sha256"],"source_snapshots":snapshots,"artifacts":artifacts,
        "child_result":identity(stage,str(result_path.relative_to(stage))) if result_path.is_file() else None,
        "child_outcome":child.get("outcome"),"counts":child.get("counts"),"successful_callbacks":child.get("successful_callbacks"),"skips":child.get("skips"),
        "runtime_observation":{"executable":sys.executable,"version":sys.version,"implementation":platform.python_implementation(),"optimize":sys.flags.optimize},
        "qualification":"Actual unittest_child result in a separate locked/no-sync process; retained lock is not installed-dependency certification; only listed ambient environment values are recorded."}
    if error:receipt["error"]=error
    path=folder/"receipt.json";write_new(path,receipt)
    if error:raise ValueError("nonpassing numerical attempt retained: "+str(path)+"; "+error)
    validate_record(stage,receipt,root)
    return {"record":str(path),"status":"passed","tests_run":receipt["counts"]["tests_run"],"successful_callbacks":receipt["successful_callbacks"]}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage",type=Path,required=True);parser.add_argument("--attempt",default="final")
    parser.add_argument("--validate",type=Path)
    args=parser.parse_args()
    result=validate_record(args.stage,args.validate) if args.validate else record_tests(args.stage,attempt=args.attempt)
    print(json.dumps(result,indent=2,allow_nan=False))


if __name__=="__main__":main()
