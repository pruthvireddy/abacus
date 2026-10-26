"""Seal a specifically selected, independently verified Phase 1 evidence bundle."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
STUDY = "23_gc_overnight_breakout_15m"


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024*1024),b""): h.update(block)
    return h.hexdigest()


def dump(path, value):
    Path(path).write_text(json.dumps(value,indent=2,allow_nan=False)+"\n")


def read_json(path):
    def unique(pairs):
        result={}
        for key,value in pairs:
            if key in result:raise ValueError("duplicate evidence JSON key")
            result[key]=value
        return result
    def nonfinite(value):raise ValueError("nonfinite evidence JSON value")
    return json.loads(Path(path).read_text(),object_pairs_hook=unique,parse_constant=nonfinite)


def safe_file(root, relative):
    """Select an ordinary local evidence file without following any symlink."""
    if not isinstance(relative,str) or not relative or "\\" in relative:
        raise ValueError("ordinary relative evidence path required")
    parts=PurePosixPath(relative)
    if parts.is_absolute() or str(parts)!=relative or any(p in (".","..","") for p in parts.parts):
        raise ValueError("unsafe evidence path")
    target=Path(root)
    if target.is_symlink():raise ValueError("no symlink evidence root")
    for part in parts.parts:
        target/=part
        if target.is_symlink():raise ValueError("no symlink evidence")
    if not target.is_file():raise ValueError("ordinary evidence file required: "+relative)
    return target


def check_pin(root, path, sha256, size=None):
    selected=safe_file(root,path)
    if size is not None and (type(size) is not int or selected.stat().st_size!=size):
        raise ValueError("evidence size mismatch: "+path)
    if digest(selected)!=sha256:raise ValueError("evidence SHA-256 mismatch: "+path)


def preflight(stage, root=ROOT):
    """Read-only lifecycle guard before making any payload/retention directory."""
    stage,root=Path(stage).resolve(),Path(root).resolve()
    owner=root/"work"/STUDY
    if not stage.is_relative_to(owner) or stage==owner:
        raise ValueError("owning unique run stage required")
    target=root/"runs"/STUDY/stage.name
    if target.exists() or target.is_symlink():raise FileExistsError("completed runs are immutable")
    if (stage/"sealed-bundle").exists():raise FileExistsError("fresh seal payload required; preserve earlier diagnostics")
    for file in stage.rglob("*"):
        if file.is_symlink():raise ValueError("no symlink evidence")
    receipts={}
    for name in ("scientific-verification.json","publication-verification.json"):
        receipt=read_json(safe_file(stage,name))
        statuses=[receipt[key] for key in ("status","result") if key in receipt]
        if not statuses or any(value!="passed" for value in statuses):
            raise ValueError("required independent gate did not pass: "+name)
        receipts[name]=receipt
    checks=read_json(safe_file(stage,"checks.json"))
    by_name={item["name"]:item for item in checks}
    if len(by_name)!=len(checks):raise ValueError("duplicate recorded check names")
    for name in ("study-numerical","independent-execution","publication-transfer","publication-contract"):
        if name not in by_name or by_name[name]["status"]!="passed":
            raise ValueError("missing required passed check "+name)
        safe_file(stage,by_name[name]["record"])
    completion=read_json(safe_file(stage,"execution-completion.json"))
    if completion["phase2"]!="uncomputed":raise ValueError("Phase2 scope violation")
    freeze=read_json(safe_file(stage,"execution-freeze.json"))
    check_pin(stage,"config.json",freeze["settings_sha256"])
    check_pin(stage,"inputs.lock.json",freeze["inputs_sha256"])
    for item in freeze["source_files"]:check_pin(stage,item["path"],item["sha256"])
    science=receipts["scientific-verification.json"]
    check_pin(stage,"environment.lock",science["verification_environment"]["environment_lock_sha256"])
    for item in science["source_versions"]:check_pin(stage,item["path"],item["sha256"],item["bytes"])
    for item in science["records"]:check_pin(stage,item["path"],item["sha256"],item["bytes"])
    publication=receipts["publication-verification.json"]
    for path,sha256 in publication["artifact_hashes"].items():check_pin(stage,path,sha256)
    if "checker_source" in publication:
        item=publication["checker_source"];check_pin(stage,item["path"],item["sha256"])
    retained=root/"data/research/sahadeva"/STUDY/stage.name
    external=read_json(safe_file(stage,"events.manifest.json"))
    for item in external:
        file=safe_file(root,item["locator"])
        if not file.is_relative_to(retained):raise ValueError("external ledger belongs to a different retention namespace")
        check_pin(root,item["locator"],item["sha256"],item["bytes"])
    audit=stage/"input-audit"
    inventory=read_json(safe_file(audit,"audit-artifacts.json"))
    for item in inventory:check_pin(audit,item["path"],item["sha256"],item["bytes"])
    audit_retained=retained/"input-audit"
    if audit_retained.exists():
        for file in audit.rglob("*"):
            if file.is_file():check_pin(audit_retained,str(file.relative_to(audit)),digest(file),file.stat().st_size)
    source_map=read_json(safe_file(stage,"source-map.json"))
    for item in source_map["source_artifacts"]:check_pin(stage,item["path"],item["sha256"])
    report=read_json(safe_file(stage,"publication.json"))
    if report["source"]["runId"]!=stage.name or source_map["run_id"]!=stage.name:
        raise ValueError("publication/run identity mismatch")
    for section in report["sections"]:
        if section["kind"]=="figure":safe_file(stage,section["path"])
    for download in report.get("downloads",[]):safe_file(stage,download["path"])
    for name in ("commands.json","exclusions.json","git-status.txt","protocol.md"):
        safe_file(stage,name)
    return target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage",type=Path,required=True)
    args = parser.parse_args()
    stage = args.stage.resolve()
    target=preflight(stage)
    payload = stage/"sealed-bundle"
    payload.mkdir(exist_ok=False)
    for path in stage.iterdir():
        if path.name in ("sealed-bundle","input-audit","publication-attempts"): continue
        if path.is_symlink(): raise ValueError("no symlink evidence")
        if path.is_dir(): shutil.copytree(path,payload/path.name)
        else: shutil.copyfile(path,payload/path.name)
    # These lifecycle helpers are authored after the research execution freeze.
    # Retain them separately, without changing executed research snapshots.
    for name in ("seal.py","save_report.py"):
        path=payload/"source-sealing"/STUDY/name
        path.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(HERE/name,path)
    path=payload/"source-sealing"/STUDY/"tests/test_lifecycle.py"
    path.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(HERE/"tests/test_lifecycle.py",path)
    retained = ROOT/"data/research/sahadeva"/STUDY/stage.name
    audit_retained = retained/"input-audit"
    if not audit_retained.exists(): shutil.copytree(stage/"input-audit",audit_retained)
    for file in (stage/"input-audit").iterdir():
        actual = audit_retained/file.name
        if file.is_symlink() or actual.is_symlink() or not actual.is_file() or digest(actual) != digest(file):
            raise ValueError("retained input audit bytes differ from verified stage")
    external = json.loads((stage/"events.manifest.json").read_text())
    # Unselected draft figures/reports are retained privately with exact pins.
    # Only the final explicitly selected report/assets enter ordinary run source.
    drafts = stage/"publication-attempts"
    draft_records = []
    if drafts.exists():
        destination = retained/"publication-attempts"
        if not destination.exists(): shutil.copytree(drafts,destination)
        for file in sorted(drafts.rglob("*")):
            if not file.is_file(): continue
            relative = str(file.relative_to(drafts))
            check_pin(destination,relative,digest(file),file.stat().st_size)
            item={"id":"presentation-draft-"+hashlib.sha256(relative.encode()).hexdigest()[:16],
                "locator":str((destination/relative).relative_to(ROOT)),
                "bytes":file.stat().st_size,"sha256":digest(file)}
            external.append(item)
            draft_records.append(item)
        dump(payload/"presentation-drafts.manifest.json",draft_records)
    copied_audit = payload/"input-audit"
    copied_audit.mkdir()
    for file in (stage/"input-audit").iterdir():
        if file.suffix == ".parquet":
            external.append({"id":"audit-"+file.stem,"locator":str((audit_retained/file.name).relative_to(ROOT)),
                "bytes":file.stat().st_size,"sha256":digest(file)})
        else: shutil.copyfile(file,copied_audit/file.name)
    for item in external:
        locator = ROOT/item["locator"]
        if not locator.is_relative_to(retained) or locator.is_symlink() or not locator.is_file():
            raise ValueError("unsafe or missing retained external artifact")
        if locator.stat().st_size != item["bytes"] or digest(locator) != item["sha256"]:
            raise ValueError("retained external artifact bytes changed")
    dump(payload/"retained-external-check.json",{"result":"passed","checked_files":len(external),
        "scope":"Actual local retained external bytes checked before sealing; general evidence validator independently leaves external declarations unverified; off-device backup not assessed."})
    # Exact source-copy paths used by the private publication audit point at the
    # forthcoming immutable run, while their bytes are checked in this payload.
    report = json.loads((payload/"publication.json").read_text())
    source_map = json.loads((payload/"source-map.json").read_text())
    source_artifacts = []
    for item in source_map["source_artifacts"]:
        artifact = item["path"]
        actual = digest(payload/artifact)
        if actual != item["sha256"]: raise ValueError("publication source pin mismatch")
        source_artifacts.append({"path":str((target/artifact).relative_to(ROOT)),"sha256":actual})
    selected = ["publication.json","source-map.json","publication-verification.json"]
    selected += [s["path"] for s in report["sections"] if s["kind"]=="figure"]
    selected += [d["path"] for d in report.get("downloads",[])]
    dump(payload/"publication-manifest.json",{"publication_id":report["id"],
        "source_run_id":stage.name,"study_id":STUDY,"source_artifacts":source_artifacts,
        "outputs":[{"path":str((target/x).relative_to(ROOT)),"sha256":digest(payload/x)} for x in selected]})
    freeze = json.loads((payload/"execution-freeze.json").read_text())
    snapshots = [str(x.relative_to(payload)) for parent in
        (payload/"source",payload/"source-publication",payload/"verification-source",payload/"verification",payload/"source-sealing")
        if parent.exists() for x in parent.rglob("*") if x.is_file()]
    artifacts = [{"path":str(p.relative_to(payload)),"bytes":p.stat().st_size,"sha256":digest(p)}
                 for p in sorted(payload.rglob("*")) if p.is_file()]
    dump(payload/"manifest.json",{"contract":"abacus.evidence/v1","bundle_kind":"research",
        "study_id":STUDY,"run_id":stage.name,"inventory_scope":"declared_artifacts",
        "results":{"kind":"quantitative","state":"computed","artifacts":["metrics.json","tables/cohorts.csv","tables/scenarios.csv"]},
        "provenance":{"settings":"config.json","input_lock":"inputs.lock.json",
            "exclusions":"exclusions.json","commands":"commands.json","checks":"checks.json",
            "environment_lock":"environment.lock","code":{"revision":freeze["revision"],
                "dirty":freeze["dirty"],"status":"git-status.txt","source_snapshot":{"paths":snapshots,
                    "scope":"Explicit executed study producer, pinned consumer dependencies and retained publication/independent-verifier bytes; not automatic dependency discovery or native TradingView verification."}}},
        "artifacts":artifacts,"external_artifacts":[{k:x[k] for k in ("id","locator","bytes","sha256")} for x in external]})
    result = subprocess.run([sys.executable,str(ROOT/"scripts/check-evidence-bundle.py"),str(payload),"--json"],
                            text=True,capture_output=True)
    (stage/"seal-integrity.log").write_text(result.stdout+result.stderr)
    if result.returncode: raise ValueError("explicit evidence contract assessment failed")
    # Copy is fresh and does not replace a run or any earlier retained artifact.
    target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copytree(payload,target)
    after = subprocess.run([sys.executable,str(ROOT/"scripts/check-evidence-bundle.py"),str(target),"--json"],
                           text=True,capture_output=True)
    if after.returncode: raise ValueError("sealed-copy integrity failed; diagnostic incomplete bundle retained")
    print(json.dumps({"result":"sealed_verified_declared_artifacts","run":str(target),
        "manifest_sha256":digest(target/"manifest.json"),"artifact_count":len(artifacts),
        "external_declarations":len(external)},indent=2))


if __name__ == "__main__": main()
