"""Reconcile evidence, retain private ledgers, seal a new immutable run."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from .spec import STUDY, PRODUCTS, MODES, PERIODS
from .storage import sha, save_json, utc_now
from .events import select_events
from .statistics import path_summary, POLICY_KEYS, policy_summary
from .reporting import check_projection, value

def verify(work):
    for name in ("freeze.json","input-audit-complete.json","scoring-complete.json","summarization-complete.json","report.md","report.html","publication.json"):
        assert (work/name).is_file(),name
    inputs=json.loads((work/"inputs.lock.json").read_text());root=Path(inputs["root_resolution"]["publication_root"])
    for r in inputs["files"]:assert sha(root/r["path"])==r["sha256"],r["path"]
    freeze=json.loads((work/"freeze.json").read_text())
    assert sha(work/"config.json")==freeze["settings_sha256"]
    assert sha(work/"protocol.md")==freeze["protocol_sha256"]
    for r in inputs["sources"]:
        source_root=Path(inputs["root_resolution"][r["root_alias"]])
        assert sha(source_root/r["path"])==r["sha256"],"Preserved source changed"
    for r in json.loads((work/"code-identity.json").read_text())["snapshot_files"]:
        assert sha(work/"code"/r["path"])==r["sha256"]
    h=pd.read_csv(work/"tables/horizons.csv",dtype={"pair":str})
    p=pd.read_csv(work/"tables/policy.csv",dtype={"pair":str})
    weekly=pd.read_csv(work/"tables/weekly.csv")
    assert len(h)==3*5*3*4*3*6
    checked=0
    for product in PRODUCTS:
        ev=pd.read_parquet(work/"private"/f"events_{product}.parquet")
        paths=pd.read_parquet(work/"private"/f"outcomes_{product}.parquet")
        orders=pd.read_parquet(work/"private"/f"ordering_{product}.parquet")
        trades=pd.read_parquet(work/"private"/f"trades_{product}.parquet")
        policy_sessions=pd.read_parquet(work/"private"/f"policy_sessions_{product}.parquet")
        bars=pd.read_parquet(work/"private"/f"bars_{product}.parquet")
        seeds=bars.groupby("segment",sort=False).head(1)
        assert np.allclose(seeds.fast,seeds.close) and np.allclose(seeds.slow,seeds.close)
        assert seeds.atr.isna().all() and (seeds.preceding==0).all()
        assert (~bars.loc[bars.preceding<250,"seed_valid"]).all()
        assert (bars.available_at==bars.ts+5*60_000_000_000).all()
        assert not ev.event_id.duplicated().any()
        assert (ev.entry_ts==ev.available_at).all() and (ev.entry_ts>ev.confirmation_ts).all()
        entered=paths[paths.entered]
        for keys,g in h[h["product"]==product].groupby(["split","pair","mode","side"]):
            split,pair,mode,side=keys
            selection=select_events(ev,pair,mode);selection=selection[selection.split==split]
            if side!="both":selection=selection[selection.side==side]
            for r in g.itertuples():
                result=path_summary(selection,paths[paths.horizon==r.horizon])
                for field in ("accepted","entered","completed_N","entry_cancelled","censored_entered","sessions","mean_delta","mean_MFE","mean_MAE","favorable_share"):
                    a=result[field];b=getattr(r,field)
                    assert (pd.isna(a) and pd.isna(b)) or np.isclose(a,b,atol=1e-8,rtol=1e-8),(product,keys,r.horizon,field,a,b)
                checked+=1
        # Binary categories partition all accepted event/horizon records, including missing.
        assert len(orders)==len(paths)*3
        assert set(orders.order)<=set(("favorable_first","adverse_first","same_minute_ambiguous","neither","censored","entry_cancelled"))
        # Every cloud selection is a subset of the shared no-filter episode opportunities.
        for pair in ("2","3","4"):
            base=set(select_events(ev,pair,"none").event_id)
            for mode in MODES[1:]:assert set(select_events(ev,pair,mode).event_id)<=base
        core=select_events(ev,"3","alignment")
        assert core.first_episode.all() and core.seed_valid.all()
        assert (core.confirmation_ts+5*60_000_000_000==core.entry_ts).all()
        session_groups={keys:g for keys,g in policy_sessions.groupby(POLICY_KEYS,dropna=False,sort=False)}
        trade_groups={keys:g for keys,g in trades.groupby(POLICY_KEYS,dropna=False,sort=False)}
        for _,r in p[p["product"]==product].iterrows():
            keys=tuple(r[k] for k in POLICY_KEYS)
            session=session_groups[keys]
            trade=trade_groups.get(keys,trades.iloc[:0])
            expected=policy_summary(session[session.split==r.split],trade[trade.split==r.split])
            for field in ("eligible_sessions","scorable_sessions","unresolved_sessions","entered_trades","resolved_trades","unresolved_trades","ambiguous_trades","mean_net_R_per_session","mean_net_R_per_trade","net_USD_resolved_trades","completed_session_drawdown_R"):
                a=expected[field];b=r[field]
                assert (pd.isna(a) and pd.isna(b)) or np.isclose(a,b,rtol=1e-8,atol=1e-8),(product,keys,r.split,field,a,b)
        for (split,mode),g in weekly[weekly["product"]==product].groupby(["split","mode"]):
            total=g[g.week=="TOTAL"].iloc[0];parts=g[g.week!="TOTAL"]
            assert parts.accepted.sum()==total.accepted and parts.completed_N.sum()==total.completed_N
            assert parts.favorable_N.sum()==total.favorable_N
            if total.completed_N:
                assert np.isclose((parts.mean_delta*parts.completed_N).sum()/total.completed_N,total.mean_delta,rtol=1e-8,atol=1e-8)
        print(f"{product}: horizon denominators, values and shared opportunities reconciled",flush=True)
    publication=json.loads((work/"publication.json").read_text());source_map=json.loads((work/"publication-source-map.json").read_text())
    tables={s["id"]:s for s in publication["sections"] if s["kind"]=="table"}
    cells=0
    for m in source_map["tables"]:
        assert sha(work/m["source"])==m["source_sha256"]
        f=pd.read_csv(work/m["source"],dtype={"pair":str})
        displayed=tables[m["section_id"]]["rows"]
        assert len(displayed)==len(m["source_row_indices"])
        for row,i in zip(displayed,m["source_row_indices"]):
            for column in m["columns"]:
                assert row[column]==value(f.loc[i,column]),(m["section_id"],i,column)
                cells+=1
    download_cells=sum(check_projection(work,p) for p in source_map["downloads"])
    assert len(publication["sections"])<=30
    assert len((work/"publication.json").read_bytes())<=96*1024
    assert all(len(t["rows"])<=100 and len(t["columns"])<=12 for t in tables.values())
    assert all(1<=d["rowCount"]<=1000 and len(d["columns"])<=24 and (work/d["path"]).stat().st_size<=256*1024 for d in publication["downloads"])
    assert sum((work/d["path"]).stat().st_size for d in publication["downloads"])<=512*1024
    log=subprocess.run([sys.executable,"-m","unittest","discover","-s",str(Path(__file__).resolve().parents[1]/"tests"),"-v"],capture_output=True,text=True)
    (work/"numerical-tests-final.log").write_text(log.stdout+log.stderr)
    assert log.returncode==0
    save_json(work/"verification.json",{"verified_at":utc_now(),"passed":True,"input_records_reverified":len(inputs["files"]),"horizon_rows_reconciled":checked,"publication_table_cells_reconciled":cells,"download_cells_reconciled":download_cells,"numerical_tests":"numerical-tests-final.log","checks":["all input hashes","preserved source hashes","code snapshot hashes","frozen specification hashes","every core horizon count and arithmetic mean","shared opportunity subsets","minute threshold category partitions","all selected Narada source/download cells","source/table/download limits","focused numerical tests"],"qualification":"Numerical reproducibility does not certify mapping arrival, annual holidays or real fills"})
    print(f"Verified {checked} horizon rows, {cells} displayed cells and {download_cells} exact download cells",flush=True)

def seal(work,root):
    verification=json.loads((work/"verification.json").read_text())
    assert verification["passed"]
    assert (work/"website-verification.json").is_file(),"Local website checks must be saved before sealing"
    destination=root/"runs"/STUDY/work.name
    publication_root=Path(json.loads((work/"inputs.lock.json").read_text())["root_resolution"]["publication_root"])
    retained=publication_root/"data/research/sahadeva"/STUDY/work.name
    if destination.exists() or retained.exists():raise RuntimeError("Immutable destination already exists")
    # Presentation and source-cell verification precede the immutable transition.
    retained.mkdir(parents=True)
    descriptors=[]
    for p in sorted((work/"private").glob("*.parquet")):
        target=retained/p.name;shutil.copy2(p,target)
        assert sha(target)==sha(p)
        metadata=pq.ParquetFile(target)
        descriptors.append({"path":str(target.relative_to(publication_root)),"root_alias":"publication_root","sha256":sha(target),"bytes":target.stat().st_size,"rows":metadata.metadata.num_rows,"columns":metadata.schema_arrow.names,"retention":"retained ignored research storage; external backup not verified","private":True})
    save_json(work/"events.manifest.json",{"study_id":STUDY,"run_id":work.name,"files":descriptors,"retention":"Retained outside ordinary Git history; preserve along with source data; backup unverified"})
    # Snapshot final report/verification source in addition to pre-score numerical source.
    source=Path(__file__).resolve().parents[1]
    for p in source.rglob("*"):
        if p.is_file() and "__pycache__" not in p.parts and p.suffix in (".py",".md",".json",".yaml"):
            target=work/"delivery-code"/p.relative_to(source);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
    save_json(work/"delivery-code-identity.json",{"created_at":utc_now(),"files":[{"path":str(p.relative_to(work)),"sha256":sha(p)} for p in sorted((work/"delivery-code").rglob("*")) if p.is_file()],"relationship":"Final report/verification code; pre-scoring numerical source is independently preserved under code/"})
    artifacts=[]
    for p in sorted(work.rglob("*")):
        if p.is_file() and "private" not in p.relative_to(work).parts and p.name not in ("manifest.json","SEALED"):
            artifacts.append({"path":str(p.relative_to(work)),"sha256":sha(p),"bytes":p.stat().st_size})
    save_json(work/"manifest.json",{"study_id":STUDY,"run_id":work.name,"sealed_at":utc_now(),"status":"verified_historical_descriptive_and_assumed_cost_simulation","protocol_version":"0.3.0-executed.2","commands":"commands.json","code_identity":"code-identity.json","delivery_code_identity":"delivery-code-identity.json","environment":"environment.json","inputs":"inputs.lock.json","checks":["verification.json","website-verification.json"],"large_evidence":"events.manifest.json","artifacts":artifacts})
    destination.parent.mkdir(parents=True,exist_ok=True)
    shutil.copytree(work,destination,ignore=shutil.ignore_patterns("private"))
    assert all(sha(destination/r["path"])==r["sha256"] for r in artifacts)
    (work/"SEALED").write_text(str(destination)+"\n")
    print(f"Sealed new evidence run: {destination}")
