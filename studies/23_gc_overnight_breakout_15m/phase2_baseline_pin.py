"""Pin the immutable, published Phase 1 authority before Phase 2 calculations.

This audit reads retained evidence and public bytes. It does not calculate any
alternative-entry, protected-boundary, recovery, or EMA-management outcome.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
from typing import Callable

STUDY = "23_gc_overnight_breakout_15m"
RUN_ID = "20261013T142537Z_phase1_gc_ob15m_v1"
RUN_MANIFEST_SHA256 = "d2f93832610ca6e6284838ce22ca9547b8c848a1b0f06a740a345df39d94c027"
PUBLICATION_ID = "gc-overnight-breakout-15m-phase1-20261013-v1"
RELEASE_ID = "20261013T172420Z_c9cd5748"
PUBLIC_ORIGIN = "https://abacus-narada.vercel.app"
STUDY_ROUTE = "/studies/gc-overnight-breakout-15m/"
REPORT_ROUTE = "/reports/"+PUBLICATION_ID+"/"
SCENARIOS = ("primary-one-tick", "gross-zero-cost", "net-zero-ticks", "net-two-ticks",
    "high-first-one-tick", "low-first-one-tick", "native-observed-one-minute",
    "source-fifteen-minute-ohlc", "source-account")
DEFAULT_GATE = ["agent-docs", "bhishma", "sahadeva", "legacy-01", "legacy-02", "vwap-doctor"]


def digest(path: Path) -> str:
    value=hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b""):value.update(chunk)
    return value.hexdigest()


def read_json(path: Path):
    def unique(pairs):
        result={}
        for key,value in pairs:
            if key in result:raise ValueError("duplicate JSON key: "+key)
            result[key]=value
        return result
    def nonfinite(value):raise ValueError("nonfinite JSON value: "+value)
    return json.loads(path.read_text(),object_pairs_hook=unique,parse_constant=nonfinite)


def ordinary_file(root: Path, relative: str) -> Path:
    if not isinstance(relative,str) or not relative or "\\"in relative:
        raise ValueError("ordinary relative path required")
    parts=PurePosixPath(relative)
    if parts.is_absolute() or str(parts)!=relative or any(x in (".","..","")for x in parts.parts):
        raise ValueError("unsafe or noncanonical path")
    target=Path(root)
    if target.is_symlink():raise ValueError("symlink root")
    for part in parts.parts:
        target/=part
        if target.is_symlink():raise ValueError("symlink evidence")
    if not target.is_file():raise ValueError("missing ordinary file: "+relative)
    return target


def verify_records(root: Path, records: list[dict], *, key="path") -> list[dict]:
    seen=set();verified=[]
    for record in records:
        name=record[key]
        if name in seen:raise ValueError("duplicate selected locator")
        seen.add(name)
        path=ordinary_file(root,name)
        if "bytes"in record and (type(record["bytes"])is not int or path.stat().st_size!=record["bytes"]):
            raise ValueError("selected byte size mismatch: "+name)
        if digest(path)!=record["sha256"]:raise ValueError("selected SHA-256 mismatch: "+name)
        verified.append(dict(path=name,bytes=path.stat().st_size,sha256=record["sha256"]))
    return verified


def verify_protocol(config: dict, scenarios: dict[str,dict]) -> None:
    fixed={"protocol_version":"1.0.0","study_id":STUDY,"product":"GC","signal_minutes":15,
        "execution_minutes":1,"broker_timezone":"fixed_UTC_plus_03:00","range_hours":[0,7],
        "entry_hours":[7,20],"stop_percent":1.0,"entries_per_broker_day":1,
        "take_profit":None,"equity_guard":False,"first_loaded_broker_day":"excluded",
        "standardized_quantity":1.0,"primary_model":"validated_native",
        "phase2_state":"unimplemented_uncomputed_unexecuted"}
    for key,value in fixed.items():
        if key not in config or config[key]!=value:raise ValueError("Phase1 baseline convention changed: "+key)
    costs=config["costs"]
    if costs["commission_fees_dollars_per_contract_per_side"]!=2.5 or costs["primary_adverse_ticks_per_fill"]!=1:
        raise ValueError("Phase1 frozen cost scenario changed")
    instrument=config["instrument"]
    if instrument!={"tick_size":.1,"dollars_per_point":100.,"minimum_quantity":1.,"quantity_step":1.}:
        raise ValueError("Phase1 executable GC economics changed")
    if set(scenarios)!=set(SCENARIOS):raise ValueError("exact nine Phase1 scenarios required")
    for name,cfg in scenarios.items():
        if cfg["signal_minutes"]!=15 or cfg["stop_percent"]!=1. or cfg["tick_size"]!=.1 or cfg["point_value"]!=100:
            raise ValueError("Phase1 scenario baseline rules changed")
        if cfg["model"]not in {"validated_native","native_strategy_approx"} or cfg["execution_minutes"]not in {1,15}:
            raise ValueError("unknown baseline scenario execution model")


def curl_get(url: str) -> dict:
    """Anonymous exact bytes; no cookies, authentication, or protection change."""
    result=subprocess.run(["curl","--fail","--silent","--show-error","--location",
        "--max-time","30","--header","Accept-Encoding: identity","--header","Cache-Control: no-cache",
        "--write-out","\nABACUS_HTTP_STATUS:%{http_code}",url],capture_output=True)
    if result.returncode:raise ValueError("anonymous public GET failed: "+url+": "+result.stderr.decode("utf-8",errors="replace"))
    body,status=result.stdout.rsplit(b"\nABACUS_HTTP_STATUS:",1)
    return dict(bytes=len(body),sha256=hashlib.sha256(body).hexdigest(),
        status=int(status),authentication="anonymous_no_cookies_or_bypass")


def verify_live(records: list[dict],fetch: Callable[[str],dict]=curl_get) -> list[dict]:
    checked=[]
    for record in records:
        response=fetch(record["url"])
        if response["status"]!=200 or response["bytes"]!=record["bytes"]or response["sha256"]!=record["sha256"]:
            raise ValueError("live Phase1 baseline bytes differ: "+record["url"])
        checked.append(dict(record,**response))
    return checked


def read_baseline_ledger(workspace: Path, record: dict) -> list[dict]:
    """Read only a selected verified original ledger; never reconstruct Phase 1."""
    verify_records(workspace,[record],key="locator")
    with gzip.open(ordinary_file(workspace,record["locator"]),"rt") as stream:
        rows=[json.loads(line)for line in stream]
    if len(rows)!=record["row_count"]:raise ValueError("original ledger row count differs")
    return rows


def audit_baseline(workspace: Path, *, live=True) -> dict:
    workspace=Path(workspace).resolve()
    run=workspace/"runs"/STUDY/RUN_ID
    manifest_file=ordinary_file(run,"manifest.json")
    if digest(manifest_file)!=RUN_MANIFEST_SHA256:raise ValueError("authoritative Phase1 manifest changed")
    manifest=read_json(manifest_file)
    if manifest["study_id"]!=STUDY or manifest["run_id"]!=RUN_ID or len(manifest["artifacts"])!=165 or len(manifest["external_artifacts"])!=124:
        raise ValueError("authoritative Phase1 inventory/identity mismatch")
    local=verify_records(run,manifest["artifacts"])
    external=verify_records(workspace,manifest["external_artifacts"],key="locator")
    market_lock=read_json(ordinary_file(run,"inputs.lock.json"))
    market=verify_records(workspace,market_lock["files"])
    source_lock=read_json(ordinary_file(run,"source/"+str(Path("studies")/STUDY/"inputs.lock.json")))
    sources=verify_records(workspace,source_lock["sources"])
    config=read_json(ordinary_file(run,"config.json"))
    scenarios={name:read_json(ordinary_file(run,"scenario-configs/"+name+".json"))for name in SCENARIOS}
    verify_protocol(config,scenarios)
    freeze=read_json(ordinary_file(run,"execution-freeze.json"))
    if digest(run/"config.json")!=freeze["settings_sha256"] or digest(run/"inputs.lock.json")!=freeze["inputs_sha256"]:
        raise ValueError("original execution settings/input freeze differs")
    if read_json(run/"execution-completion.json")["phase2"]!="uncomputed":
        raise ValueError("Phase1 authority contains alternative-entry execution")
    events=read_json(ordinary_file(run,"events.manifest.json"))
    ids={item["id"]:item for item in events}
    ledger_records=[];ledger_counts={}
    for scenario in SCENARIOS:
        ledger_counts[scenario]={}
        for kind in ("trades","orders","events","days"):
            identifier=scenario+"-"+kind
            if identifier not in ids:raise ValueError("required Phase1 ledger absent")
            record=ids[identifier]
            rows=read_baseline_ledger(workspace,record)
            ledger_records.append(record)
            ledger_counts[scenario][kind]=len(rows)
    release_root=workspace/"apps/narada/releases"/RELEASE_ID
    release=read_json(ordinary_file(release_root,"release.json"))
    outcome=read_json(ordinary_file(release_root,"outcome.json"))
    if outcome["result"]!="passed" or outcome["sourceRunId"]!=RUN_ID or outcome["sourceRunManifestSha256"]!=RUN_MANIFEST_SHA256 or outcome["publicationId"]!=PUBLICATION_ID:
        raise ValueError("Phase1 production authority differs")
    pub=next(x for x in release["publications"]if x["id"]==PUBLICATION_ID)
    public_bundle=read_json(ordinary_file(workspace,"apps/narada/public/publications/"+PUBLICATION_ID+"/report.json"))
    # Narada sourceSha256 identifies stable JavaScript JSON serialization, not
    # the original producer file bytes. Those original bytes were verified by
    # the sealed inventory; preserve both distinct hash meanings explicitly.
    if (pub["sourceRunId"]!=RUN_ID or public_bundle["report"]!=read_json(run/"publication.json")
            or public_bundle["provenance"]["sourceSha256"]!=pub["sourceSha256"]):
        raise ValueError("immutable Phase1 publication source differs")
    app=workspace/"apps/narada"
    payload=app/release["artifact"]
    all_static={x["path"]:x for x in release["staticFiles"]}
    selected_names=["studies/gc-overnight-breakout-15m/index.html",
        "reports/"+PUBLICATION_ID+"/index.html","publications/"+PUBLICATION_ID+"/report.json"]
    selected_names += ["publications/"+PUBLICATION_ID+"/"+x["path"]for x in pub["assets"]]
    selected=[all_static[name]for name in selected_names]
    verify_records(payload/".vercel/output/static",selected)
    for name in selected_names:
        if name.startswith("publications/"):verify_records(app/"public",[all_static[name]])
    live_records=[]
    for row in selected:
        suffix=row["path"][:-len("index.html")]if row["path"].endswith("index.html")else row["path"]
        live_records.append(dict(url=PUBLIC_ORIGIN+"/"+suffix,**row))
    live_result=verify_live(live_records)if live else []
    registry=read_json(workspace/"config/workspace-checks.json")
    if registry["default_profile"]!="default" or registry["profiles"]["default"]["checks"]!=DEFAULT_GATE:
        raise ValueError("default compatibility gate changed")
    audit_files={x["id"]:x for x in manifest["external_artifacts"]if x["id"].startswith("audit-")}
    return dict(schema_version="abacus.study23.phase2-baseline-pin/v1",status="passed",checked_at=datetime.now(timezone.utc).isoformat(),
        study_id=STUDY,phase2_outcomes_calculated=False,phase1_run_id=RUN_ID,
        phase1_manifest=dict(path=str(manifest_file.relative_to(workspace)),sha256=RUN_MANIFEST_SHA256),
        local_artifacts=[dict(x,path=str((run/x["path"]).relative_to(workspace)))for x in local],
        retained_external_artifacts=manifest["external_artifacts"],selected_market_input_pins=market,retained_source_pins=sources,
        baseline_protocol=dict(path=str((run/"protocol.md").relative_to(workspace)),sha256=digest(run/"protocol.md")),
        baseline_config=dict(path=str((run/"config.json").relative_to(workspace)),sha256=digest(run/"config.json"),settings=config),
        original_market_lock=dict(path=str((run/"inputs.lock.json").relative_to(workspace)),sha256=digest(run/"inputs.lock.json")),
        scenario_configs=scenarios,scenario_ledgers=ledger_records,scenario_ledger_counts=ledger_counts,
        prepared_execution_inputs=audit_files,
        coverage_roster=dict(path=str((run/"input-audit/coverage-roster.csv").relative_to(workspace)),sha256=digest(run/"input-audit/coverage-roster.csv")),
        complete_day_roster=dict(path=str((run/"tables/days.csv").relative_to(workspace)),sha256=digest(run/"tables/days.csv")),
        publication=dict(publication_id=PUBLICATION_ID,release_id=RELEASE_ID,study_url=PUBLIC_ORIGIN+STUDY_ROUTE,
            report_url=PUBLIC_ORIGIN+REPORT_ROUTE,static_records=selected,live_checked=live,live_records=live_result),
        counts=dict(local=165,retained_external=124,selected_market_inputs=len(market),sources=len(sources),scenario_ledgers=len(ledger_records),selected_static=len(selected),live_files=len(live_result)),
        default_gate_preserved=True,prior_exposure="All Phase1 annual baseline outcomes already public; no Phase2 untouched-holdout claim",
        preserved_qualifications=market_lock.get("timestamp_semantics",{}),
        limits=["This checks retained baseline and publication byte identities; it does not reproduce statistics or establish native TradingView parity.",
            "One-minute OHLC and modeled available_at timing retain intraminute, live latency and leader-mapping qualifications.",
            "Original raw reconstruction, annual holiday certification and off-device backup remain unverified.",
            "Live byte GETs are HTTP evidence, not a new interactive browser review."])


def write_new_audit(workspace: Path, stage: Path, result: dict) -> None:
    workspace=Path(workspace).resolve();stage=Path(stage).resolve()
    owner=workspace/"work"/STUDY
    if not stage.is_relative_to(owner)or stage==owner or stage.name==RUN_ID:
        raise ValueError("new Phase2 study stage required")
    folder=stage/"baseline-pin"
    if (stage/"phase2-baseline-pin.json").exists():raise FileExistsError("fresh Phase2 baseline pin required")
    folder.mkdir(parents=True,exist_ok=False)
    for name,value in (("phase1-baseline.pin.json",result),("baseline-audit.json",dict(status=result["status"],checked_at=result["checked_at"],counts=result["counts"],phase1_manifest=result["phase1_manifest"],phase2_outcomes_calculated=False,live_checked=result["publication"]["live_checked"],limits=result["limits"]))):
        with (folder/name).open("x")as stream:json.dump(value,stream,indent=2,allow_nan=False);stream.write("\n")
    with (stage/"phase2-baseline-pin.json").open("x")as stream:
        json.dump(result,stream,indent=2,allow_nan=False);stream.write("\n")


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace",type=Path,required=True)
    parser.add_argument("--stage",type=Path,required=True)
    parser.add_argument("--skip-live",action="store_true")
    args=parser.parse_args()
    result=audit_baseline(args.workspace,live=not args.skip_live)
    write_new_audit(args.workspace,args.stage,result)
    print(json.dumps(dict(status=result["status"],counts=result["counts"],manifest=result["phase1_manifest"],live_checked=result["publication"]["live_checked"],phase2_outcomes_calculated=False),indent=2))


if __name__=="__main__":main()
