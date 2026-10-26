"""Seal one explicitly verified new Phase 2 run; never overwrite evidence.

The root-owned sealing-inputs.json chooses exact receipts, source snapshots,
23 publication inventories and retained external records. This lifecycle gate
checks their bytes and recorded scopes; it never executes numerical producers,
exporters or recorded commands, and does not substitute integrity for science.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
STUDY="23_gc_overnight_breakout_15m"
SCHEMA="study23.phase2-sealing-inputs/v1"
GATES=("science","metrics","account","publication_transfer","publication_contract","numerical")
RUNTIME={"phase2_run.py","phase2_metrics.py","phase2_accounts.py","metrics.py","src/engine.py","src/phase2_engine.py"}
GENERATED={"manifest.json","sealing-aliases.json","retained-external-check.json","sealing-completion.json"}
SKIP={"sealed-bundle","seal-integrity.log","seal-copy-integrity.log"}


def digest(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda:stream.read(1024*1024),b""):h.update(block)
    return h.hexdigest()


def read_json(path):
    def unique(pairs):
        result={}
        for key,value in pairs:
            if key in result:raise ValueError("duplicate evidence JSON key: "+key)
            result[key]=value
        return result
    def number(value):
        result=float(value)
        if not math.isfinite(result):raise ValueError("nonfinite evidence JSON number")
        return result
    def constant(value):raise ValueError("nonfinite evidence JSON constant")
    return json.loads(Path(path).read_text(encoding="utf-8"),object_pairs_hook=unique,parse_constant=constant,parse_float=number)


def write_new(path,value):
    with Path(path).open("x",encoding="utf-8") as stream:
        json.dump(value,stream,indent=2,allow_nan=False);stream.write("\n")


def relative(value):
    if not isinstance(value,str) or not value or any(c in value for c in ("\\","%","\0")):
        raise ValueError("plain safe relative evidence path required")
    parts=value.split("/")
    if PurePosixPath(value).is_absolute() or any(p in {"",".",".."} for p in parts):
        raise ValueError("unsafe evidence path: "+value)
    return value


def ordinary(path,*,directory=False,absent=False):
    if ".." in Path(path).parts:raise ValueError("path traversal refused")
    selected=Path(os.path.abspath(path))
    for parent in reversed(selected.parents):
        if parent.is_symlink() or (parent.exists() and not parent.is_dir()):raise ValueError("redirected evidence ancestor")
    if selected.is_symlink():raise ValueError("symlink evidence refused")
    if absent:
        if os.path.lexists(selected):raise FileExistsError("existing evidence must be preserved: "+str(selected))
    elif directory:
        if not selected.is_dir():raise ValueError("ordinary evidence directory required")
    elif not selected.exists() or not stat.S_ISREG(selected.stat().st_mode):raise ValueError("ordinary evidence file required: "+str(selected))
    return selected


def safe_file(base,path):return ordinary(Path(base)/relative(path))


def pin(base,record,cache=None):
    path=relative(record["path"])
    size=record.get("bytes")
    sha=record.get("sha256")
    if size is not None and (type(size) is not int or size<0):raise ValueError("invalid evidence byte count")
    if not isinstance(sha,str) or not re.fullmatch(r"[0-9a-f]{64}",sha):raise ValueError("invalid evidence SHA-256")
    file=safe_file(base,path)
    key=str(file)
    actual=(file.stat().st_size,digest(file)) if cache is None or key not in cache else cache[key]
    if cache is not None:cache[key]=actual
    if (size is not None and actual[0]!=size) or actual[1]!=sha:raise ValueError("evidence bytes changed: "+path)
    return file


def identity(base,path):
    file=safe_file(base,path)
    return {"path":path,"bytes":file.stat().st_size,"sha256":digest(file)}


def passed(record,label):
    values=[record[key] for key in ("status","result","outcome") if key in record]
    if not values or any(value!="passed" for value in values):raise ValueError("required gate did not pass: "+label)


def instant(value):
    result=datetime.fromisoformat(str(value).replace("Z","+00:00"))
    if result.tzinfo is None:raise ValueError("aware receipt chronology required")
    return result.astimezone(timezone.utc)


def _pins_from_receipt(stage,receipt,cache):
    artifacts=receipt.get("artifacts",receipt.get("records",[]))
    bound=set()
    for item in artifacts:
        pin(stage,item,cache);bound.add(item["path"])
    for path,sha in receipt.get("artifact_hashes",{}).items():
        pin(stage,{"path":path,"sha256":sha},cache);bound.add(path)
    for field in ("source_snapshots","source_versions","source_files"):
        for item in receipt.get(field,[]):pin(stage,item,cache)
    if "checker_source" in receipt:pin(stage,receipt["checker_source"],cache)
    if "source_snapshot" in receipt:
        pin(stage,{"path":receipt["source_snapshot"],"sha256":receipt["checker_sha256"]},cache)
    if "source_snapshot" not in receipt and not any(receipt.get(key) for key in ("source_snapshots","source_versions","source_files","checker_source")):
        raise ValueError("receipt must retain actual checker/test source bytes")
    return bound


def _baseline(root,record,cache):
    passed(record,"baseline pin")
    if record.get("study_id")!=STUDY or record.get("phase2_outcomes_calculated") is not False:
        raise ValueError("baseline pin scope mismatch")
    for field in ("phase1_manifest","baseline_protocol","baseline_config","original_market_lock","coverage_roster","complete_day_roster"):
        pin(root,record[field],cache)
    for field in ("local_artifacts","selected_market_input_pins","retained_source_pins"):
        for item in record.get(field,[]):pin(root,item,cache)
    external=[]
    for item in [*record.get("retained_external_artifacts",[]),*record.get("scenario_ledgers",[]),*record.get("prepared_execution_inputs",{}).values()]:
        pin(root,{"path":item["locator"],"bytes":item["bytes"],"sha256":item["sha256"]},cache)
        external.append(item)
    return external


def _phase_pin(stage,root,record,cache):
    selected=pin(root,record,cache)
    if not selected.is_relative_to(stage):raise ValueError("executed ledger outside selected stage")
    return str(selected.relative_to(stage))


def _numeric(stage,record,freeze,cache,root):
    if record.get("schema_version")!="study23.phase2-numerical-record/v1":raise ValueError("actual stage-bound numerical record schema required")
    counts=record.get("counts")
    if not isinstance(counts,dict):raise ValueError("structured numerical TestResult required")
    for name in ("discovered","tests_run","failures","errors","skipped","expected_failures","unexpected_successes"):
        if type(counts.get(name)) is not int or counts[name]<0:raise ValueError("invalid numerical count")
    if counts["discovered"]!=counts["tests_run"] or counts["tests_run"]<=counts["skipped"] or any(counts[k] for k in ("failures","errors","unexpected_successes")):
        raise ValueError("numerical suite did not actually pass meaningful tests")
    if type(record.get("successful_callbacks")) is not int or record["successful_callbacks"]<=0:
        raise ValueError("numerical success callbacks required")
    if record.get("environment_lock_sha256")!=freeze["environment_lock_sha256"] or record.get("execution_freeze_sha256")!=digest(stage/"execution-freeze.json"):
        raise ValueError("numerical record belongs to different frozen stage")
    argv=record.get("command",record.get("argv",[]))
    if not isinstance(argv,list) or not all(isinstance(s,str) and s for s in argv) or "--locked" not in argv or "--no-sync" not in argv:
        raise ValueError("record exact locked no-sync numerical command")
    child=read_json(pin(stage,record["child_result"],cache))
    if child.get("outcome")!="passed" or any(record[field]!=child[field] for field in ("counts","successful_callbacks","skips")):
        raise ValueError("numerical receipt cannot replace actual child TestResult")
    for item in record["source_snapshots"]:
        pin(root,{"path":item["original_workspace_path"],"bytes":item["bytes"],"sha256":item["sha256"]},cache)


def _publication(stage,entry,cache):
    path=relative(entry["path"])
    if len(PurePosixPath(path).parts)!=2 or PurePosixPath(path).parts[0]!="publications":raise ValueError("explicit immutable publication directory required")
    directory=ordinary(stage/path,directory=True)
    declared={}
    for item in entry["files"]:
        if item["path"] in declared:raise ValueError("duplicate publication inventory path")
        pin(directory,item,cache);declared[item["path"]]=item
    actual={str(p.relative_to(directory)) for p in directory.rglob("*") if p.is_file()}
    if set(declared)!=actual:raise ValueError("publication inventory must cover every selected byte")
    for name in ("publication.json","source-map.json","publication-manifest.json"):
        if name not in declared:raise ValueError("publication required source metadata absent")
    report=read_json(directory/"publication.json");mapping=read_json(directory/"source-map.json")
    manifest=read_json(directory/"publication-manifest.json")
    if report["id"]!=directory.name or report["source"]["runId"]!=stage.name or mapping.get("run_id")!=stage.name or mapping.get("publication_id")!=directory.name:
        raise ValueError("publication/run identity mismatch")
    if type(mapping.get("source_row_base")) is not int or mapping["source_row_base"]!=0:raise ValueError("publication source rows must remain zero-based integers")
    if manifest.get("publication_id")!=directory.name or manifest.get("source_run_id")!=stage.name or manifest.get("study_id")!=STUDY:
        raise ValueError("per-publication manifest identity mismatch")
    future_prefix="runs/"+STUDY+"/"+stage.name+"/publications/"+directory.name+"/"
    selected={}
    groups={}
    for group in ("source_artifacts","outputs"):
        records=manifest.get(group)
        if not isinstance(records,list) or not records:raise ValueError("nonempty per-publication source/output pins required")
        paths=set()
        for item in records:
            workspace_path=relative(item["path"])
            if not workspace_path.startswith(future_prefix):raise ValueError("per-publication source/output path outside future immutable directory")
            local=relative(workspace_path[len(future_prefix):])
            if local in paths:raise ValueError("duplicate per-publication manifest "+group+" path")
            paths.add(local)
            pin(directory,{"path":local,"sha256":item["sha256"]},cache)
            if local in selected and selected[local]!=item["sha256"]:raise ValueError("conflicting source/output manifest hashes")
            selected[local]=item["sha256"]
        groups[group]=paths
    if not {"publication.json","source-map.json","publication-verification.json"}<=groups["outputs"]:
        raise ValueError("per-publication manifest lacks required final verified outputs")
    verification=read_json(safe_file(directory,"publication-verification.json"));passed(verification,"per-publication verification")
    if verification.get("publication_sha256") is not None and verification["publication_sha256"]!=digest(directory/"publication.json"):
        raise ValueError("per-publication verified report bytes changed")
    if verification.get("source_map_sha256") is not None and verification["source_map_sha256"]!=digest(directory/"source-map.json"):
        raise ValueError("per-publication verified source-map bytes changed")
    for item in mapping["source_artifacts"]:
        pin(directory,{"path":item["path"],"sha256":item["sha256"]},cache)
        pin(stage,{"path":item["original_stage_source_path"],"sha256":item["original_source_sha256"]},cache)
        if item["path"] not in groups["source_artifacts"]:raise ValueError("copied publication source lacks future manifest source pin")
    for section in report["sections"]:
        if section["kind"]=="figure":
            safe_file(directory,section["path"])
            if section["path"] not in groups["outputs"]:raise ValueError("selected figure lacks final manifest output pin")
    for item in report.get("downloads",[]):
        selected=safe_file(directory,item["path"])
        if digest(selected)!=item["sha256"]:raise ValueError("declared download changed")
        if item["path"] not in groups["outputs"]:raise ValueError("selected download lacks final manifest output pin")
    for item in mapping.get("figures",[]):
        pin(directory,{"path":item["svg_path"],"sha256":item["svg_sha256"]},cache)
        image_path=item.get("image_path",item.get("path"))
        pin(directory,{"path":image_path,"sha256":item["image_sha256"]},cache)
    return report["id"]


def _validate(stage,root,*,payload_allowed=False):
    root=ordinary(root,directory=True);stage=ordinary(stage,directory=True)
    if stage.parent!=root/"work"/STUDY or not re.fullmatch(r"\d{8}T\d{6}Z_[a-z0-9_-]+",stage.name):
        raise ValueError("owning direct unique UTC run stage required")
    target=root/"runs"/STUDY/stage.name
    ordinary(target,absent=True)
    if not payload_allowed:
        ordinary(stage/"sealed-bundle",absent=True)
        for name in ("seal-integrity.log","seal-copy-integrity.log"):ordinary(stage/name,absent=True)
    for item in stage.rglob("*"):
        if item.is_symlink():raise ValueError("symlink staged evidence refused")
    for name in GENERATED:
        if (stage/name).exists():raise ValueError("generated sealer output already exists in stage")
    cache={}
    inputs=read_json(safe_file(stage,"sealing-inputs.json"))
    if inputs.get("schema_version")!=SCHEMA or inputs.get("run_id")!=stage.name:raise ValueError("explicit sealing identity mismatch")
    config=read_json(safe_file(stage,"config.json"));freeze=read_json(safe_file(stage,"execution-freeze.json"))
    if config.get("run_id")!=stage.name or config.get("protocol_version")!="2.0.0" or config.get("phase3_state")!="unimplemented_uncomputed":raise ValueError("Phase 2 frozen scope mismatch")
    if type(freeze.get("dirty")) is not bool or not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}",str(freeze.get("revision"))):raise ValueError("actual code revision/dirty identity required")
    for name,key in (("config.json","settings_sha256"),("protocol.md","protocol_sha256"),("inputs.lock.json","inputs_sha256"),("phase2-baseline-pin.json","baseline_pin_sha256"),("environment.lock","environment_lock_sha256")):
        pin(stage,{"path":name,"sha256":freeze[key]},cache)
    if not freeze.get("source_files"):raise ValueError("actual executed source snapshot required")
    prefix="source/studies/"+STUDY+"/"
    if not RUNTIME<={item["path"][len(prefix):] for item in freeze["source_files"] if item["path"].startswith(prefix)}:
        raise ValueError("frozen runtime producer scope incomplete")
    for item in freeze["source_files"]:
        pin(stage,item,cache)
        if item["path"].startswith(prefix) and item["path"][len(prefix):] in RUNTIME:
            pin(root,{"path":item["path"].removeprefix("source/"),"sha256":item["sha256"],"bytes":item["bytes"]},cache)
    baseline=read_json(stage/"phase2-baseline-pin.json")
    baseline_external=_baseline(root,baseline,cache)
    lock=read_json(stage/"inputs.lock.json")
    if lock.get("sha256")!=freeze["baseline_pin_sha256"] or config.get("baseline_manifest_sha256")!=baseline["phase1_manifest"]["sha256"]:
        raise ValueError("executed input/baseline identities diverge")
    selections=read_json(safe_file(stage,"selection.json"));selection_freeze=read_json(safe_file(stage,"selection-freeze.json"))
    if selections.get("later_alternative_outcomes_opened") is not False or selection_freeze.get("later_outcomes_opened") is not False:
        raise ValueError("selection must be frozen before later outcomes")
    if selection_freeze["selection_sha256"]!=digest(stage/"selection.json") or selection_freeze["settings_sha256"]!=freeze["settings_sha256"]:
        raise ValueError("selection bytes/settings changed")
    dev=read_json(safe_file(stage,"phases/dev-validation/completion.json"));later=read_json(safe_file(stage,"phases/later/completion.json"))
    if dev.get("original_years")!=["2018","2019","2020","2021","2022","2023"] or later.get("original_years")!=["2024","2025","2026"]:
        raise ValueError("chronological episode splits changed")
    phase_artifacts=set()
    for label,phase in (("dev-validation",dev),("later",later)):
        if phase["settings_sha256"]!=freeze["settings_sha256"] or phase["selection_sha256"]!=selection_freeze["selection_sha256"]:
            raise ValueError("phase execution pin mismatch")
        phase_artifacts.add("phases/"+label+"/completion.json")
        pinned={_phase_pin(stage,root,item,cache) for item in phase["ledgers"]}
        expected={"phases/"+label+"/"+name+".jsonl.gz" for name in ("policies","occurrence","recovery","boundary-events","level-opportunities")}
        if pinned!=expected or len(phase["ledgers"])!=len(expected):raise ValueError("complete fixed phase ledger set required")
        phase_artifacts.update(pinned)
    if selection_freeze["development_validation_ledger"] not in dev["ledgers"]:raise ValueError("selection must pin actual development/validation ledger")
    starts=read_json(pin(stage,inputs["chronology"],cache))
    start_record=starts.get("later",starts)
    if start_record["selection_sha256"]!=selection_freeze["selection_sha256"] or start_record["settings_sha256"]!=freeze["settings_sha256"]:
        raise ValueError("later-launch record selection/settings mismatch")
    start_at=start_record.get("started_at",start_record.get("later_started_at"))
    dev_receipt=read_json(pin(stage,{"path":start_record["independent_dev_verification_path"],"sha256":start_record["independent_dev_verification_sha256"]},cache))
    passed(dev_receipt,"independent development/validation before later launch")
    if instant(dev_receipt["finished_at"])>instant(start_at):raise ValueError("independent development verification finished after later launch")
    completion=read_json(safe_file(stage,"execution-completion.json"))
    if completion.get("phase2")!="computed" or completion.get("phase3")!="uncomputed" or completion["settings_sha256"]!=freeze["settings_sha256"] or completion["selection_sha256"]!=selection_freeze["selection_sha256"]:
        raise ValueError("completed execution scope/identity mismatch")
    if dev["episodes"]+later["episodes"]!=baseline["scenario_ledger_counts"]["primary-one-tick"]["trades"] or completion["episodes"]!=dev["episodes"]+later["episodes"]:
        raise ValueError("full accepted baseline episode roster must be retained")
    clock=[freeze["at"],selections["frozen_at"],selection_freeze["frozen_at"],dev["finished_at"],start_at,later["finished_at"],completion["finished_at"]]
    if [instant(t) for t in clock]!=sorted(instant(t) for t in clock):raise ValueError("selection/later launch chronology out of order")
    metrics=read_json(safe_file(stage,"metrics.json"))
    tables=set()
    for name,item in metrics["tables"].items():
        path="tables/"+relative(name)+".csv";pin(stage,{"path":path,"sha256":item["sha256"]},cache);tables.add(path)
    checks=read_json(safe_file(stage,"checks.json"));commands=read_json(safe_file(stage,"commands.json"))
    if not isinstance(checks,list) or len({r["name"] for r in checks})!=len(checks):raise ValueError("unique recorded checks required")
    if not isinstance(commands,list) or not commands:raise ValueError("exact command records required")
    for command in commands:
        if not isinstance(command.get("argv"),list) or not command["argv"] or not all(isinstance(x,str) and x for x in command["argv"]) or not isinstance(command.get("cwd"),str):raise ValueError("invalid exact command record")
    for name in ("exclusions.json","git-status.txt","report.md","report.html","advice.md"):safe_file(stage,name)
    receipts={};bound={}
    if not isinstance(inputs["receipts"],dict) or not set(GATES)<=set(inputs["receipts"]):raise ValueError("all mandatory independent receipts required")
    for name,record in inputs["receipts"].items():
        receipt=read_json(pin(stage,record,cache));passed(receipt,name)
        if not any(r["status"]=="passed" and r.get("record")==record["path"] for r in checks):raise ValueError("required receipt lacks a recorded passed check: "+name)
        receipts[name]=receipt;bound[name]=_pins_from_receipt(stage,receipt,cache)
    scientific={"config.json","protocol.md","inputs.lock.json","phase2-baseline-pin.json","execution-freeze.json","selection.json","selection-freeze.json",*phase_artifacts}
    if not scientific<=bound["science"]:raise ValueError("scientific receipt is not bound to all frozen phase evidence")
    if not {"metrics.json",*tables}<=bound["metrics"]:raise ValueError("metrics receipt does not cover saved tables")
    if not {"account-settings.json","account-ledger.jsonl.gz","tables/account.csv","tables/account-capacity.csv"}<=bound["account"]:raise ValueError("account receipt does not cover actual accounts/capacity")
    _numeric(stage,receipts["numerical"],freeze,cache,root)
    sources=inputs["source_snapshots"]
    if not {"verifier","exporter","sealer"}<={s.get("role") for s in sources}:raise ValueError("verifier/exporter/sealer source copies required")
    for item in sources:pin(stage,item,cache)
    if not any(s.get("role")=="sealer" and s["sha256"]==digest(HERE/"phase2_seal.py") for s in sources):raise ValueError("actual sealing implementation snapshot required")
    publications=inputs["publications"]
    ids=[_publication(stage,item,cache) for item in publications]
    actual_dirs={p.name for p in ordinary(stage/"publications",directory=True).iterdir() if p.is_dir()}
    if len(ids)!=23 or len(set(ids))!=23 or set(ids)!=actual_dirs:raise ValueError("exactly 23 explicit report bundles required")
    checked=receipts["publication_transfer"].get("publications",[])
    if {r["publication_id"] for r in checked}!=set(ids) or len(checked)!=23:raise ValueError("independent transfer did not verify all 23 reports")
    for item in checked:
        passed(item,"selected publication")
        prefix="publications/"+item["publication_id"]+"/"
        for path,key in (("publication.json","publication_sha256"),("source-map.json","source_map_sha256"),("publication-manifest.json","publication_manifest_sha256")):
            pin(stage,{"path":prefix+path,"sha256":item[key]},cache)
        if prefix+"publication.json" not in bound["publication_contract"]:raise ValueError("publication contract receipt must pin every selected report")
    external=[];ids_external=set();locators={}
    for item in inputs.get("external_artifacts",[]):
        if item["id"] in ids_external:raise ValueError("duplicate retained external identity")
        ids_external.add(item["id"])
        file=pin(root,{"path":item["locator"],"bytes":item["bytes"],"sha256":item["sha256"]},cache)
        if not file.is_relative_to(root/"data/research/sahadeva"/STUDY/stage.name):raise ValueError("new external evidence belongs to another retention namespace")
        if "source_stage_path" in item:
            pin(stage,{"path":item["source_stage_path"],"bytes":item["bytes"],"sha256":item["sha256"]},cache)
            if item["source_stage_path"] in locators:raise ValueError("duplicate retained source alias")
            locators[item["source_stage_path"]]=item
        external.append(item)
    private=inputs.get("private_staged_files",[])
    if len(private)!=len(set(private)) or not set(private)<=set(locators):raise ValueError("private source aliases require exact retained byte pins")
    if any(not path.endswith((".jsonl.gz",".parquet")) for path in private):raise ValueError("only private bulk ledgers/inputs may move to sealed event aliases")
    if any((stage/("events/"+path)).exists() for path in private):raise ValueError("sealed private alias would collide with existing staged evidence")
    for path in inputs["results_artifacts"]:safe_file(stage,path)
    if not {"metrics.json","tables/paired.csv","tables/account.csv"}<=set(inputs["results_artifacts"]):raise ValueError("core computed results must be declared")
    return target,inputs,freeze,external,baseline_external


def preflight(stage,root=ROOT):
    """Read-only refusal gate; no retained directory or payload is created."""
    return _validate(stage,root)[0]


def seal(stage,root=ROOT):
    stage=ordinary(stage,directory=True);root=ordinary(root,directory=True)
    target,inputs,freeze,external,baseline_external=_validate(stage,root)
    initial={str(p.relative_to(stage)):identity(stage,str(p.relative_to(stage))) for p in stage.rglob("*") if p.is_file() and p.relative_to(stage).parts[0] not in SKIP}
    payload=stage/"sealed-bundle";payload.mkdir(exist_ok=False)
    aliases=[]
    for path,item in initial.items():
        destination="events/"+path if path in inputs.get("private_staged_files",[]) else path
        file=payload/destination;file.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(stage/path,file)
        pin(payload,{**item,"path":destination})
        if destination!=path:aliases.append({"source_stage_path":path,"sealed_local_path":destination,"bytes":item["bytes"],"sha256":item["sha256"]})
    _validate(stage,root,payload_allowed=True)
    for path,item in initial.items():pin(stage,item)
    write_new(payload/"sealing-aliases.json",{"schema_version":"study23.phase2-sealing-aliases/v1","run_id":stage.name,"aliases":aliases,
        "external_source_aliases":[item for item in external if "source_stage_path" in item],
        "qualification":"Original execution receipts and workspace paths remain unchanged; aliases identify byte-identical retained copies."})
    write_new(payload/"retained-external-check.json",{"status":"passed","new_external_files":len(external),"reused_baseline_external_records":len(baseline_external),
        "scope":"Actual local retained bytes independently hashed before sealing; general evidence contract leaves external declarations unverified; no off-device backup claim."})
    write_new(payload/"sealing-completion.json",{"status":"passed","run_id":stage.name,"phase2":"computed","phase3":"uncomputed",
        "at":datetime.now(timezone.utc).isoformat(),"selected_publications":23,"sealing_inputs_sha256":digest(stage/"sealing-inputs.json")})
    snapshots=[s["path"] for s in freeze["source_files"]]+[s["path"] for s in inputs["source_snapshots"]]
    for item in inputs["receipts"].values():
        receipt=read_json(stage/item["path"])
        for field in ("source_snapshots","source_versions","source_files"):
            snapshots.extend(s["path"] for s in receipt.get(field,[]))
        if "source_snapshot" in receipt:snapshots.append(receipt["source_snapshot"])
        if "checker_source" in receipt:snapshots.append(receipt["checker_source"]["path"])
    artifacts=[identity(payload,str(p.relative_to(payload))) for p in sorted(payload.rglob("*")) if p.is_file()]
    externals=[{k:item[k] for k in ("id","locator","bytes","sha256")} for item in external]
    baseline_unique={item["locator"]:item for item in baseline_external}
    externals+=[{"id":"reused-baseline-"+hashlib.sha256(path.encode()).hexdigest()[:24],"locator":path,"bytes":item["bytes"],"sha256":item["sha256"]} for path,item in sorted(baseline_unique.items())]
    write_new(payload/"manifest.json",{"contract":"abacus.evidence/v1","bundle_kind":"research","study_id":STUDY,"run_id":stage.name,
        "inventory_scope":"declared_artifacts","results":{"kind":"quantitative","state":"computed","artifacts":inputs["results_artifacts"]},
        "provenance":{"settings":"config.json","input_lock":"inputs.lock.json","exclusions":"exclusions.json","commands":"commands.json","checks":"checks.json",
            "environment_lock":"environment.lock","code":{"revision":freeze["revision"],"dirty":freeze["dirty"],"status":"git-status.txt",
                "source_snapshot":{"paths":sorted(set(snapshots)),"scope":"Frozen executed Phase 2 producers and explicit independent-verifier/exporter/sealer source copies; no automatic dependency completeness or native TradingView claim."}}},
        "artifacts":artifacts,"external_artifacts":externals})
    checker=ROOT/"scripts/check-evidence-bundle.py"
    result=subprocess.run([sys.executable,str(checker),str(payload),"--json"],capture_output=True,text=True)
    with (stage/"seal-integrity.log").open("x") as stream:stream.write(result.stdout+result.stderr)
    if result.returncode:raise ValueError("prepared evidence contract failed; preserve diagnostic payload")
    ordinary(target,absent=True);target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copytree(payload,target)
    after=subprocess.run([sys.executable,str(checker),str(target),"--json"],capture_output=True,text=True)
    with (stage/"seal-copy-integrity.log").open("x") as stream:stream.write(after.stdout+after.stderr)
    if after.returncode:raise ValueError("sealed-copy integrity failed; preserve incomplete diagnostic run")
    return {"result":"sealed_verified_declared_artifacts","run":str(target),"manifest_sha256":digest(target/"manifest.json"),
            "artifact_count":len(artifacts),"selected_publications":23,"external_declarations":len(externals)}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage",type=Path,required=True);parser.add_argument("--preflight",action="store_true")
    args=parser.parse_args()
    if args.preflight:print(json.dumps({"result":"preflight_passed","target":str(preflight(args.stage))},indent=2))
    else:print(json.dumps(seal(args.stage),indent=2))


if __name__=="__main__":main()
