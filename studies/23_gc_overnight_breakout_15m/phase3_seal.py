"""Fail-closed sealing of a uniquely staged, independently verified Phase3 run.

Source report content is finalized before sealing. Large declared ledgers are
retained separately with byte identities; earlier runs/releases are untouched.
"""
from __future__ import annotations

import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import shutil
import subprocess

from phase2_seal import ordinary,relative,safe_file,pin,identity,digest,read_json,write_new,passed

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
STUDY="23_gc_overnight_breakout_15m"
GATES={"inputs","numerical","development_validation","science","publication_transfer","publication_contract","visual_review"}


def preflight(stage,root=ROOT):
    stage=ordinary(stage,directory=True)
    spec=read_json(stage/"sealing-inputs.json")
    if spec.get("schema_version")!="study23.phase3-sealing-inputs/v1" or spec.get("run_id")!=stage.name:raise ValueError("explicit Phase3 stage sealing identity required")
    if not spec.get("publication_sources_prepared_before_seal"):raise ValueError("prepared sources required")
    freeze=pin(stage,spec["execution_freeze"])
    frozen=read_json(freeze)
    pin(stage,spec["settings"]);pin(stage,spec["protocol"]);pin(stage,spec["environment_lock"])
    completion=read_json(pin(stage,spec["completion"]))
    if completion.get("phase3")!="computed":raise ValueError("actual complete Phase3 execution required")
    if spec["settings"]["sha256"]!=frozen["settings_sha256"]:raise ValueError("settings do not match executed freeze")
    for source in frozen["source_files"]:
        pin(stage,source)
        # Retained test snapshots may be supplemented by later presentation
        # tests. Executed runtime bytes must still match the computational freeze.
        if source.get("workspace_path") in {"phase3_run.py","phase3_execution.py","phase3_inputs.py","phase3_metrics.py","phase3_verify.py","src/phase3_engine.py","src/engine.py"}:
            pin(HERE,{"path":source["workspace_path"],"sha256":source["sha256"]})
    if set(spec["gates"])!=GATES:raise ValueError("exact independent and visual gate roster required")
    for name,record in spec["gates"].items():
        receipt=read_json(pin(stage,record));passed(receipt,name)
        if receipt.get("run_id",stage.name)!=stage.name:raise ValueError("gate belongs to another run")
        for artifact in record.get("bound_artifacts",[]):pin(stage,artifact)
        for source in record.get("checker_sources",[]):pin(stage,source)
        if name!="inputs" and not record.get("checker_sources"):raise ValueError("retain actual checker/reviewer source or review record")
        if name=="numerical":
            counts=receipt["counts"]
            if counts["discovered"]!=counts["tests_run"] or counts["tests_run"]<=0 or any(counts[k] for k in ("failures","errors","skipped","unexpected_successes")):raise ValueError("actual meaningful suite did not pass")
            if receipt["execution_freeze_sha256"]!=digest(freeze) or receipt["successful_callbacks"]<=0:raise ValueError("suite freeze/callback mismatch")
    selection=read_json(pin(stage,spec["selection"]))
    selectionfreeze=read_json(pin(stage,spec["selection_freeze"]))
    if selectionfreeze["selection_sha256"]!=spec["selection"]["sha256"] or selectionfreeze.get("later_outcomes_opened") is not False:raise ValueError("selection must freeze before later outcomes")
    dev=read_json(stage/"phases/dev-validation/completion.json");later=read_json(stage/"phases/later/completion.json")
    # Chronology fields are aware UTC timestamps, never inferred file mtimes.
    def time(value):return datetime.fromisoformat(value.replace("Z","+00:00"))
    if time(selectionfreeze["frozen_at"])<time(dev["finished_at"]) or time(later["started_at"])<time(selectionfreeze["frozen_at"]):raise ValueError("chronological execution/selection violated")
    external=[]
    for record in spec.get("parent_and_input_external",[]):
        pin(root,{"path":record["locator"],"sha256":record["sha256"],"bytes":record["bytes"]});external.append(record)
    publications=spec["publications"]
    if len(publications)!=19 or len({p["publication_id"] for p in publications})!=19:raise ValueError("complete seven-condition report roster required")
    for publication in publications:
        directory=stage/"publications"/publication["publication_id"]
        manifest=read_json(pin(stage,publication["manifest"]))
        verified=read_json(directory/"publication-verification.json");passed(verified,"exact report transfer")
        report=directory/"publication.json";mapping=directory/"source-map.json"
        if verified.get("publication_sha256",verified.get("report_sha256"))!=digest(report) or verified["source_map_sha256"]!=digest(mapping):raise ValueError("verified report bytes mismatch")
        if manifest["source_run_id"]!=stage.name:raise ValueError("publication parent identity mismatch")
        for item in manifest["outputs"]:
            prefix=f"runs/{STUDY}/{stage.name}/"
            if not item["path"].startswith(prefix):raise ValueError("publication output belongs to another run")
            pin(stage,{"path":item["path"][len(prefix):],"sha256":item["sha256"]})
    return {"status":"passed","run_id":stage.name,"publications":len(publications),"external_input_declarations":len(external),"scope":"Recorded science/numerical/report gates and exact frozen bytes, not a fresh research replay."}


def seal(stage,root=ROOT):
    stage=ordinary(stage,directory=True);preflight(stage,root)
    run=root/"runs"/STUDY/stage.name
    ordinary(run,absent=True)
    externalroot=root/"data/research/sahadeva"/STUDY/stage.name/"phase3-ledgers"
    ordinary(externalroot,absent=True)
    externalroot.mkdir(parents=True,exist_ok=False)
    external=[];aliases=[]
    spec=read_json(stage/"sealing-inputs.json")
    external.extend(spec.get("parent_and_input_external",[]))
    exclude={"sealed-bundle"}
    payload=stage/"sealed-bundle";ordinary(payload,absent=True);payload.mkdir()
    for source in sorted(stage.rglob("*")):
        rel=source.relative_to(stage)
        if any(part in exclude for part in rel.parts):continue
        if source.is_symlink():raise ValueError("sealed evidence symlinks prohibited")
        if not source.is_file():continue
        if source.suffixes[-2:]==[".jsonl",".gz"] and rel.parts[0] in {"phases","parents","diagnostics"}:
            dest=externalroot/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,dest)
            record={"id":"phase3-"+str(rel).replace("/","-"),"locator":str(dest.relative_to(root)),"bytes":dest.stat().st_size,"sha256":digest(dest)}
            if record["sha256"]!=digest(source):raise ValueError("retained external copy mismatch")
            external.append(record);aliases.append({"stage_path":str(rel),**record});continue
        dest=payload/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,dest)
    write_new(payload/"sealing-aliases.json",{"run_id":stage.name,"aliases":aliases,"scope":"Exact large-ledger copies; stage aliases are not rewritten into completed prior runs."})
    write_new(payload/"retained-external-check.json",{"status":"passed","run_id":stage.name,"verified_at":datetime.now(timezone.utc).isoformat(),"records":external,"scope":"Actual retained declared bytes hashed separately from generic evidence contract."})
    sourcefiles=read_json(stage/"execution-freeze.json")["source_files"]
    commandpath=spec.get("commands_path","commands.json")
    safe_file(payload,commandpath)
    sourcepath=spec.get("git_status_path","git-status.txt");safe_file(payload,sourcepath)
    checks=[{"name":name,"status":"passed","record":record["path"]} for name,record in spec["gates"].items()]
    write_new(payload/"checks.json",checks)
    files=[identity(payload,str(path.relative_to(payload))) for path in sorted(payload.rglob("*")) if path.is_file()]
    revision=subprocess.check_output(["git","rev-parse","HEAD"],cwd=root,text=True).strip()
    manifest={"contract":"abacus.evidence/v1","bundle_kind":"research","study_id":STUDY,"run_id":stage.name,"inventory_scope":"declared_artifacts","results":{"kind":"quantitative","state":"computed","artifacts":["execution-completion.json","tables/paired.csv","tables/trade-cohorts.csv","tables/profiles.csv"]},"provenance":{"settings":spec["settings"]["path"],"input_lock":spec["input_lock_path"],"exclusions":spec["exclusions_path"],"commands":commandpath,"checks":"checks.json","environment_lock":spec["environment_lock"]["path"],"code":{"revision":revision,"dirty":True,"status":sourcepath,"source_snapshot":{"paths":[r["path"] for r in sourcefiles],"scope":"Actual dedicated Phase3 computational source, audited adapters and runtime helpers; unrelated dirty workspace state is preserved separately."}}},"artifacts":files,"external_artifacts":external}
    write_new(payload/"manifest.json",manifest)
    result=subprocess.run(["python3",str(root/"scripts/check-evidence-bundle.py"),str(payload),"--json"],capture_output=True,text=True)
    (stage/"seal-integrity.log").write_text(result.stdout+result.stderr)
    if result.returncode:raise ValueError("retained candidate payload failed explicit contract check")
    shutil.copytree(payload,run)
    for record in files:pin(run,record)
    if digest(run/"manifest.json")!=digest(payload/"manifest.json"):raise ValueError("completed run copy mismatch")
    return {"status":"sealed","run_id":stage.name,"manifest_sha256":digest(run/"manifest.json"),"local_artifacts":len(files),"external_declarations":len(external),"run_path":str(run),"publications":19}


if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--stage",type=Path,required=True);p.add_argument("--seal",action="store_true");a=p.parse_args();print(json.dumps(seal(a.stage) if a.seal else preflight(a.stage),indent=2))
