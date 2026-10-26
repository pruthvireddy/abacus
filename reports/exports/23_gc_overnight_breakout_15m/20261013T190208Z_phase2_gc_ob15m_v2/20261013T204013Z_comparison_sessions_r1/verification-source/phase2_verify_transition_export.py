"""Independent saved-cell/coverage audit of post-seal transition presentation.

The original 336-test numerical receipt and all existing research/publication
bytes remain unchanged. A pinned copy of the earlier independent transfer core
checks original saved bytes → copied cells → displayed cells/downloads/plots;
this wrapper adds the newly required full transition and entry-cohort coverage.
No producer, strategy engine or statistics method is imported.
"""
from __future__ import annotations
import argparse
from collections import defaultdict
from datetime import datetime,timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys

STUDY="23_gc_overnight_breakout_15m"
RUN="20261013T190208Z_phase2_gc_ob15m_v2"
MANIFEST="ffe43f2403520d9ba058720908ad711b88e665b0d8d3928bdaa5342ad7cb3c4a"
POLICIES=("reclaim-q000","reclaim-q025","reclaim-q050","reclaim-q075","passive-q025","passive-q050","passive-q075","protected-touch-hold","protected-failed-break-reclaim","protected-reversal")
PROTECTED=POLICIES[-3:]


def require(ok,message):
    if not ok:raise ValueError(message)


def digest(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):h.update(chunk)
    return h.hexdigest()


def source_display_coverage(report,mapping,source_path,original_rows,required_rows,columns):
    """Require exact full row support for each declared displayed source cell."""
    expected={i for i,row in enumerate(original_rows) if required_rows(row)}
    table_ids={section["id"] for section in report["sections"] if section["kind"]=="table"}
    observed=defaultdict(set)
    for binding in mapping["bindings"]:
        if binding.get("original_stage_source_path")==source_path and binding["section"] in table_ids:
            column=binding.get("original_source_column")
            if column in columns:observed[column].add(binding["original_source_row"])
    for column in columns:
        require(expected<=observed[column],"complete displayed source roster: "+source_path+":"+column)
    return len(expected)*len(columns)


def transition_download_partition(source,publication,report,mapping,rows):
    required=source/"tables/transitions.csv"
    matches=[record for record in mapping["downloads"] if record["original_stage_source_path"]=="tables/transitions.csv"]
    original=[i for i,row in enumerate(rows) if row["transition"].startswith("breakout_to_candidate_entry:")]
    boundary=[i for i,row in enumerate(rows) if not row["transition"].startswith("breakout_to_candidate_entry:")]
    selected_rows=[record["original_source_rows"] for record in matches]
    require(len(matches)==2 and sorted(selected_rows)==sorted([original,boundary]),"exact two ordered original/boundary transition projections")
    require(not set(original)&set(boundary) and set(original)|set(boundary)==set(range(len(rows))),"lossless complete disjoint transition partition")
    records=[]
    for record in matches:
        require(record["columns"]==list(rows[0]),"public transition projections preserve all original saved columns")
        selected=next(r for r in report["downloads"] if r["id"]==record["id"])
        target=publication/selected["path"]
        records.append(dict(path=selected["path"],bytes=target.stat().st_size,sha256=digest(target),rows=len(record["original_source_rows"])))
    full=[record for record in mapping["source_artifacts"] if record["original_stage_source_path"]=="tables/transitions.csv" and record.get("selected_source_rows")==list(range(len(rows)))]
    require(full and any((publication/record["path"]).read_bytes()==required.read_bytes() for record in full),"private full source CSV retains byte identity")
    return dict(downloads=records,total_rows=len(rows),transition_types=len({r["transition"] for r in rows}),private_source_sha256=digest(required))


def verify_coverage(core,source,comparison,protected):
    _,transition_rows=core.table(source/"tables/transitions.csv")
    trade_columns,trade_rows=core.table(source/"tables/trade-cohorts.csv")
    time_columns,time_rows=core.table(source/"additional/time-recovery/time-recovery.csv")
    expected_types={"breakout_to_breach","breach_to_price_reclaim",*("breakout_to_candidate_entry:"+p for p in POLICIES),*("breach_to_candidate_entry:"+p for p in POLICIES)}
    require(len(transition_rows)==16500 and {r["transition"] for r in transition_rows}==expected_types,"all22 sealed transition types")
    require(all(sum(r["transition"]==kind for r in transition_rows)==750 for kind in expected_types),"750 saved transition rows per kind")
    compared=0;result={}
    report=core.json_file(comparison/"publication.json");mapping=core.json_file(comparison/"source-map.json")
    result["complete_transition_downloads"]=transition_download_partition(source,comparison,report,mapping,transition_rows)
    transition_columns=("year","side","from_session","to_session","count","unknown")
    for policy in POLICIES:
        compared+=source_display_coverage(report,mapping,"tables/transitions.csv",transition_rows,lambda r,p=policy:r["transition"]=="breakout_to_candidate_entry:"+p,transition_columns)
    report=core.json_file(protected/"publication.json");mapping=core.json_file(protected/"source-map.json")
    for policy in PROTECTED:
        for prefix in ("breakout_to_candidate_entry:","breach_to_candidate_entry:"):
            compared+=source_display_coverage(report,mapping,"tables/transitions.csv",transition_rows,lambda r,p=policy,pre=prefix:r["transition"]==pre+p,transition_columns)
        compared+=source_display_coverage(report,mapping,"tables/trade-cohorts.csv",trade_rows,lambda r,p=policy:r["policy"]==p,("year","session","side","executable_fills","completed","censored","win_rate","net_dollars","mean_net_dollars","mean_dollars_low","mean_dollars_high","profit_factor"))
    compared+=source_display_coverage(report,mapping,"tables/transitions.csv",transition_rows,lambda r:r["transition"]=="breach_to_price_reclaim",transition_columns)
    expected_trade_rows=[i for i,row in enumerate(trade_rows) if row["policy"] in PROTECTED]
    complete_trade_downloads=[r for r in mapping["downloads"] if r["original_stage_source_path"]=="tables/trade-cohorts.csv" and r["original_source_rows"]==expected_trade_rows ]
    require(len(complete_trade_downloads)==1,"complete protected450-row entry performance download")
    result["protected_full_performance_download"]={"rows":len(expected_trade_rows),"declared_columns":complete_trade_downloads[0]["columns"],"full_private_source_columns":len(trade_columns),"original_source_sha256":digest(source/"tables/trade-cohorts.csv")}
    require(len(time_rows)==1800,"full separately frozen timing cohort roster")
    compared+=source_display_coverage(report,mapping,"additional/time-recovery/time-recovery.csv",time_rows,lambda r:True,[c for c in time_columns if c!="anchor"])
    result.update(status="passed",coverage_cells=compared,source_transition_rows=16500,source_transition_types=22,original_to_candidate_policies=len(POLICIES),protected_entry_policies=len(PROTECTED),time_recovery_rows=1800)
    return result


def verify_report(core,source,root,expected_id):
    report=core.json_file(core.ordinary(root,"publication.json"));mapping=core.json_file(core.ordinary(root,"source-map.json"))
    require(report["id"]==mapping["publication_id"]==expected_id,"explicit new immutable presentation identity")
    require(report["source"]["runId"]==mapping["run_id"]==RUN,"unchanged source-run identity")
    require(mapping["source_run_manifest_sha256"]==MANIFEST,"presentation source manifest pin")
    projection=core.Projection(source,root,mapping)
    result=dict(publication_id=expected_id,status="passed",publication_sha256=digest(root/"publication.json"),source_map_sha256=digest(root/"source-map.json"),
                copied_source_artifacts=len(projection.pins),original_to_copy_cells=projection.source_cells,
                displayed_cells=core.display_cells(report,mapping,projection),download_cells=core.downloads(report,mapping,projection),claim_source_cells=core.claims(report,mapping,projection))
    result["figures"],result["figure_saved_cells"]=core.figures(report,mapping,projection)
    paths=["publication.json","source-map.json",*[r["path"] for r in mapping["source_artifacts"]],*[r["path"] for r in report.get("downloads",[])],*[r[k] for r in mapping.get("figures",[]) for k in ("path","svg_path")]]
    result["artifacts"]=[dict(path=path,bytes=core.ordinary(root,path).stat().st_size,sha256=digest(core.ordinary(root,path))) for path in sorted(set(paths))]
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--comparison",required=True,type=Path)
    parser.add_argument("--protected",required=True,type=Path)
    parser.add_argument("--attempt-directory",required=True,type=Path)
    parser.add_argument("--finalize-from",type=Path,help="passing initial receipt; verify final inventories without replacing per-report receipts")
    args=parser.parse_args();workspace=Path(__file__).resolve().parents[2]
    source=workspace/"runs"/STUDY/RUN
    require(digest(source/"manifest.json")==MANIFEST,"unchanged sealed source manifest")
    roots=[args.comparison.resolve(),args.protected.resolve()]
    for root in roots:
        allowed=root.is_relative_to(workspace/"reports/exports") or root.is_relative_to(workspace/"work"/STUDY/"20261013T204013Z_phase2_session_revision")
        require(allowed and root.is_dir() and not root.is_symlink(),"new presentation stage/export directory only")
    output=args.attempt_directory.resolve()
    require(output.is_relative_to(workspace/"work"/STUDY),"verification writes only new owning work attempt")
    output.mkdir(parents=True,exist_ok=False)
    numerical=json.loads((source/"numerical-tests/final-v1/receipt.json").read_text())
    selected=next(r for r in numerical["source_snapshots"] if r["original_workspace_path"]=="studies/"+STUDY+"/phase2_verify_publication.py")
    original_core=source/selected["path"]
    require(digest(original_core)==selected["sha256"],"frozen independent core snapshot identity")
    snapshots=[]
    for original,targetname in ((original_core,"independent_transfer_core.py"),(Path(__file__),Path(__file__).name),(Path(__file__).parent/"tests/test_phase2_transition_export.py","test_phase2_transition_export.py")):
        target=output/targetname;shutil.copyfile(original,target)
        snapshots.append(dict(path=str(target.relative_to(workspace)),bytes=target.stat().st_size,sha256=digest(target)))
    spec=importlib.util.spec_from_file_location("frozen_phase2_transfer_core",output/"independent_transfer_core.py")
    core=importlib.util.module_from_spec(spec);spec.loader.exec_module(core)
    receipt=dict(schema_version="study23.phase2-postseal-transition-transfer/v1",source_run_id=RUN,source_run_manifest_sha256=MANIFEST,command=sys.argv,started_at=datetime.now(timezone.utc).isoformat(),source_snapshots=snapshots)
    try:
        results=[]
        for root,identity in zip(roots,("gc-overnight-breakout-15m-phase2-session-transitions-20261013-r1","gc-overnight-breakout-15m-phase2-protected-entry-20261013-r1")):
            results.append(verify_report(core,source,root,identity))
        receipt["coverage"]=verify_coverage(core,source,*roots)
        receipt["publications"]=results
        artifacts=[dict(path=str((source/path).relative_to(workspace)),bytes=(source/path).stat().st_size,sha256=digest(source/path)) for path in ("manifest.json","tables/transitions.csv","tables/trade-cohorts.csv","additional/time-recovery/time-recovery.csv")]
        if args.finalize_from:
            initial=core.json_file(args.finalize_from)
            require(initial["status"]=="passed" and initial["source_run_manifest_sha256"]==MANIFEST,"passing postseal initial transfer prerequisite")
            for pin in initial["artifacts"]:
                path=workspace/pin["path"]
                require(path.stat().st_size==pin["bytes"] and digest(path)==pin["sha256"],"initial presentation/source bytes unchanged")
        for root,result in zip(roots,results):
            result.update(schema_version="study23.phase2-presentation-transfer/v1",source_run_manifest_sha256=MANIFEST,checker_sha256=digest(output/Path(__file__).name),core_checker_sha256=digest(output/"independent_transfer_core.py"))
            target=root/"verification.json"
            if not args.finalize_from:
                own_sources=[]
                for recorded in snapshots:
                    filename=Path(recorded["path"]).name
                    selected=root/"verification-source"/filename;selected.parent.mkdir(exist_ok=True)
                    shutil.copyfile(workspace/recorded["path"],selected)
                    own_sources.append(dict(path=str(selected.relative_to(root)),bytes=selected.stat().st_size,sha256=digest(selected)))
                result.update(result="passed",source_snapshots=own_sources,coverage=receipt["coverage"],scope="Post-seal saved-cell/CSV/plot transfer and complete requested transition/entry/timing roster coverage; no scientific recalculation.")
                with target.open("x") as f:json.dump(result,f,indent=2,allow_nan=False);f.write("\n")
            else:
                require(target.is_file() and core.json_file(target)["status"]=="passed","passing per-report transfer receipt")
                manifest=core.json_file(root/"manifest.json")
                require(manifest["publication_id"]==result["publication_id"] and manifest["source_run_id"]==RUN,"postseal manifest identity")
                selected_files=set()
                for pin in manifest["outputs"]:
                    path=workspace/pin["path"]
                    require(path.is_relative_to(root) and digest(path)==pin["sha256"],"postseal manifest output byte identity")
                    selected_files.add(str(path.relative_to(root)))
                require(selected_files=={str(p.relative_to(root)) for p in root.rglob("*") if p.is_file() and p.name!="manifest.json"},"complete postseal final manifest inventory")
                for pin in manifest["source_artifacts"]:
                    require(digest(workspace/pin["path"])==pin["sha256"],"postseal manifest original source byte identity")
                result["publication_manifest_sha256"]=digest(root/"manifest.json")
            artifacts.extend(dict(pin,path=str(root.relative_to(workspace))+"/"+pin["path"]) for pin in result["artifacts"])
            for own in result.get("source_snapshots",[]):
                artifacts.append(dict(own,path=str(root.relative_to(workspace))+"/"+own["path"]))
            for name in ("verification.json",*(('manifest.json',) if args.finalize_from else ())):
                path=root/name;artifacts.append(dict(path=str(path.relative_to(workspace)),bytes=path.stat().st_size,sha256=digest(path)))
        require(digest(source/"manifest.json")==MANIFEST,"sealed source unchanged after presentation audit")
        receipt.update(status="passed",result="passed",finished_at=datetime.now(timezone.utc).isoformat(),artifacts=artifacts,limits=["Post-seal selected saved-table presentation only; no new outcome calculation or retuning.","The original336-test numerical record remains unchanged; this new presentation/checker suite has separate receipts.","Actual raster/browser appearance and production verification remain separate root gates."])
    except Exception as error:
        receipt.update(status="failed",finished_at=datetime.now(timezone.utc).isoformat(),error=type(error).__name__+": "+str(error));raise
    finally:
        with (output/"receipt.json").open("x") as f:json.dump(receipt,f,indent=2,allow_nan=False);f.write("\n")
    print(json.dumps(receipt,indent=2,allow_nan=False))


if __name__=="__main__":main()
