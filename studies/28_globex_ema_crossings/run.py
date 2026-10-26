"""Freeze and execute study28 into a fresh stage; rendering uses saved tables."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import importlib.metadata
import json
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import numpy as np
import pandas as pd

STUDY=Path(__file__).resolve().parent
WORKSPACE=STUDY.parents[1]
sys.path.insert(0,str(STUDY))
from src.inputs import sha, prepare_inputs,load_product,build_panel,read_audit
from src.engine import make_tables
from src.reporting import render


def write_json(path,value):
    path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')


def sources():
    files=[p for p in STUDY.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix in ['.py','.md','.json','.yaml']]
    files += list((WORKSPACE/'packages/bhishma/src/abacus_bhishma').glob('*.py'))
    files += [WORKSPACE/'pyproject.toml',WORKSPACE/'uv.lock',WORKSPACE/'.python-version',WORKSPACE/'packages/bhishma/pyproject.toml',WORKSPACE/'packages/sahadeva/pyproject.toml']
    return sorted(files)


def freeze(stage,argv):
    inventory=[]
    for p in sources():
        rel=p.relative_to(WORKSPACE)
        dest=stage/'provenance/source'/rel
        dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
        inventory.append({'path':rel.as_posix(),'retained':dest.relative_to(stage).as_posix(),'sha256':sha(p)})
    write_json(stage/'provenance/source-inventory.json',inventory)
    status=subprocess.run(['git','status','--porcelain=v1'],cwd=WORKSPACE,capture_output=True,check=True,text=True).stdout
    (stage/'provenance/git-status.txt').write_text(status)
    diff=subprocess.run(['git','diff','--binary','HEAD'],cwd=WORKSPACE,capture_output=True,check=True).stdout
    (stage/'provenance/git-diff.patch').write_bytes(diff)
    revision=subprocess.run(['git','rev-parse','HEAD'],cwd=WORKSPACE,capture_output=True,check=True,text=True).stdout.strip()
    env={'python':sys.version,'executable':sys.executable,'platform':platform.platform(),
         'lock_sha256':sha(WORKSPACE/'uv.lock'),'packages':{d.metadata['Name']:d.version for d in importlib.metadata.distributions()}}
    write_json(stage/'provenance/environment.json',env)
    write_json(stage/'provenance/execution.json',{'started_utc':datetime.now(timezone.utc).isoformat(),
        'argv':argv,'cwd':str(WORKSPACE),'git_revision':revision,'dirty':bool(status),
        'scope':'Declared producer, Bhishma Python sources and environment lock retained before data calculation; not dependency closure or installed-environment certification.'})
    for p in ['study.yaml','inputs.lock.json','protocol-1.1.0.md']:
        shutil.copy2(STUDY/p,stage/p)
    settings={'study_id':STUDY.name,'protocol_version':'1.1.0','products':['ES','NQ','GC'],
      'primary_timeframe':'3m','timeframes':['3m'],'ema_period':6,'ema_warmup_min_preceding_bars':250,
      'common_calendar':['2021-06-28','2026-09-18'],'atr_lookback':252,'atr_max_age_days':7,
      'atr_percentile_cuts':[1/3,2/3],'range_atr_cuts':[.75,1.25],
      'bootstrap':{'replicates':2000,'block_observed_sessions':5,'seed':20261023},
      'exclusions':'Unchanged published retrospective product-day eligibility; unknown volatility is retained as unknown.',
      'derivation':'Study-local 3m OHLCV and HLC3/volume Globex VWAP via retained Bhishma helpers; no published3m feature release',
      'previous_run':'20261023T202400Z_ema6_v1'}
    write_json(stage/'config.json',settings)
    return inventory


def execution(stage,argv,plot_python):
    stage.mkdir(parents=True,exist_ok=False)
    (stage/'tables').mkdir();(stage/'figures').mkdir();(stage/'provenance').mkdir()
    inventory=freeze(stage,argv)
    print('Frozen execution source and settings',flush=True)
    root,manifests=prepare_inputs(WORKSPACE,STUDY,stage)
    print('Pinned input bytes verified',flush=True)
    all_frames=[];daily=[]
    for product in ['ES','NQ','GC']:
        frames,context=load_product(root,manifests,product)
        for f in frames:
            all_frames.append(f)
            daily.append(build_panel(f,context))
        print(f'{product}: Three-minute derivation, EMA/source parity and session panels complete',flush=True)
    bars=pd.concat(all_frames,ignore_index=True)
    bars.to_parquet(stage/'bar_evidence.parquet',index=False)
    event_columns=['product','timeframe','session_date','ts_event','bar_close_ts','available_at','bar_position','raw_symbol','close','ema6','globex_vwap','direction']
    bars.loc[bars.direction != 0,event_columns].to_csv(stage/'crossings.csv',index=False)
    panel=pd.concat(daily,ignore_index=True)
    panel['cohort']='all_available'
    common=panel[panel.session_date.between('2021-06-28','2026-09-18')].copy()
    common['cohort']='common_calendar'
    sets=[set(common.loc[common['product']==p,'session_date']) for p in ['ES','NQ','GC']]
    matched_dates=sorted(set.intersection(*sets))
    matched=common[common.session_date.isin(matched_dates)].copy();matched['cohort']='matched_dates'
    panel=pd.concat([panel,common,matched],ignore_index=True)
    panel.to_csv(stage/'daily_panel.csv',index=False)
    audit=read_audit(root);audit.to_csv(stage/'input_audit.csv',index=False)
    cov=[]
    for (p,tf),g in bars.groupby(['product','timeframe']):
        dates=sorted(g.session_date.unique())
        lo,hi=pd.Period(dates[0][:7]),pd.Period(dates[-1][:7])
        for month in pd.period_range(lo,hi,freq='M'):
            rows=g[g.session_date.str.startswith(str(month))]
            # All audit years are retained separately; coverage grid shows every month in observed span.
            ar=audit[(audit['product']==p) & audit.session_date.astype(str).str.startswith(str(month))]
            cov.append({'product':p,'timeframe':tf,'month':str(month),'eligible_sessions':rows.session_date.nunique(),
                        'audit_candidate_sessions':len(ar),'observed_bars':len(rows),
                        'has_evidence':len(rows)>0,'first_session':rows.session_date.min() if len(rows) else None,
                        'last_session':rows.session_date.max() if len(rows) else None})
    pd.DataFrame(cov).to_csv(stage/'tables/coverage.csv',index=False)
    print('Saved daily panels, crossing ledger, full bar evidence and coverage',flush=True)
    tables=make_tables(panel)
    for name,table in tables.items():table.to_csv(stage/f'tables/{name}.csv',index=False)
    print('Summary/year/month/distribution tables complete',flush=True)
    plot=subprocess.run([plot_python,str(STUDY/"render_figures.py"),str(stage)],cwd=WORKSPACE,capture_output=True,text=True)
    (stage/"figure-rendering.log").write_text(plot.stdout+plot.stderr)
    if plot.returncode: raise RuntimeError("figure rendering failed; see figure-rendering.log")
    render(stage)
    for r in inventory:
        if sha(WORKSPACE/r['path']) != r['sha256']:
            raise ValueError(f"source changed during execution: {r['path']}")
    tests=subprocess.run([sys.executable,'-m','unittest','discover','-s',str(STUDY/'tests')],cwd=WORKSPACE,capture_output=True,text=True)
    (stage/'numerical-tests.log').write_text(tests.stdout+tests.stderr)
    if tests.returncode:raise RuntimeError('numerical suite failed')
    write_json(stage/'execution-complete.json',{'completed_utc':datetime.now(timezone.utc).isoformat(),
      'source_unchanged':True,'input_bytes_verified':True,'matched_dates':len(matched_dates),
      'bar_rows':len(bars),'event_rows':int((bars.direction != 0).sum()),'daily_panel_rows':len(panel),
      'tests':{'argv':[sys.executable,'-m','unittest','discover','-s',str(STUDY/'tests')],'exit_code':tests.returncode,'log':'numerical-tests.log'},
      'independent_verification':'pending separate verifier; stage not sealed'})
    print(f'Stage complete: {stage}',flush=True)


def main():
    p=argparse.ArgumentParser();p.add_argument('--run-id',required=True);p.add_argument('--plot-python',default=sys.executable);a=p.parse_args()
    if '/' in a.run_id or a.run_id in ['.','..']:p.error('run ID must be one path component')
    execution(WORKSPACE/'work'/STUDY.name/a.run_id,[sys.executable,*sys.argv],a.plot_python)


if __name__=='__main__':main()
