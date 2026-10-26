"""Stage, audit, freeze, execute and seal only a new unique local run."""
from __future__ import annotations
import shutil,subprocess,sys,platform,importlib.metadata
from pathlib import Path
import numpy as np
import pandas as pd
from .common import OWNER,STUDY,Q,SEED,now,sha,dump,load,roots,dictionary,save_table
from .inputs import verify_pins,read_chart,input_audit
from .events import extract
from .bootstrap import Bootstrap
from .models import select,evaluate,TRANSFORM
from .analysis import summarize

NUMERICAL=['common.py','inputs.py','events.py','models.py','bootstrap.py','analysis.py','execution.py']
def prepare(out):
    out=Path(out).resolve()
    if out.exists():raise FileExistsError('Prepare requires a new unique directory')
    out.mkdir(parents=True);(out/'evidence').mkdir();(out/'provenance').mkdir()
    lock=verify_pins(out);shutil.copy2(OWNER/'inputs.lock.json',out/'inputs.lock.json')
    audits=[];dates=set()
    for entry in lock['files']:
        if entry['kind']!='enhanced':continue
        bars=read_chart(entry);audits.append(input_audit(entry,bars));dates.update(bars.session_date_proxy.tolist())
        bars.to_parquet(out/'evidence'/(bars.chart.iloc[0]+'-bars.parquet'),index=False)
        print('Input/clock/price identity verified:',bars.chart.iloc[0],flush=True)
    save_table(out,'input-quality',audits);assert sum(r['rows'] for r in audits)==lock['source_rows_total']
    dates=sorted(dates);embargo=[]
    for boundary in ['2020-01-01','2023-01-01']:
        embargo.extend([max(d for d in dates if d<boundary),min(d for d in dates if d>=boundary)])
    dump(out/'config.json',{'study_id':STUDY,'protocol_version':'2.0.0','stage':'prepared','frozen_at_utc':None,
      'bootstrap_replicates':2000,'bootstrap_seed':SEED,'constant_q_i':Q,'fixed_point_scale':10**9,
      'excluded_sessions':['2017-07-21','2026-10-01'],'embargo_dates':embargo,'observed_session_dates':dates,
      'chronology':{'development':'2017-2019','validation':'2020-2022','later':'2023-2026'},
      'ordinary_choices':'See executable-protocol.md, frozen plan and feature dictionary',
      'model_nonnegative_log1p_features':TRANSFORM,'external_publication':False,'clock_reconverted':False})
    dump(out/'feature-dictionary.json',dictionary())
    env={'python':sys.version,'platform':platform.platform(),'packages':{d.metadata['Name']:d.version for d in importlib.metadata.distributions()},
     'git_revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=roots().workspace_root,text=True).strip(),
     'uv_lock_sha256':sha(roots().workspace_root/'uv.lock'),'data_paths':{'publication':str(roots().publication_root),'legacy':str(roots().legacy_research_root)}}
    dump(out/'provenance'/'environment.json',env);shutil.copy2(roots().workspace_root/'uv.lock',out/'provenance'/'uv.lock')
    (out/'provenance'/'initial-git-status.txt').write_text(subprocess.check_output(['git','status','--porcelain=v1'],cwd=roots().workspace_root,text=True))
    (out/'provenance'/'initial-tracked-dirty.patch').write_bytes(subprocess.check_output(['git','diff','--binary','HEAD'],cwd=roots().workspace_root))
    shutil.copy2(roots().workspace_root/'config/paths.example.toml',out/'provenance'/'paths.example.toml')
    shutil.copy2(roots().workspace_root/'packages/bhishma/src/abacus_bhishma/paths.py',out/'provenance'/'paths.py')
    dump(out/'execution-status.json',{'status':'inputs_audited','at_utc':now()})

def freeze(out):
    out=Path(out).resolve();assert load(out/'execution-status.json')['status']=='inputs_audited'
    assert not (out/'freeze.json').exists()
    test=subprocess.run([sys.executable,'-m','unittest','discover','-s',str(OWNER/'tests'),'-v'],capture_output=True,text=True)
    (out/'provenance'/'pre-freeze-tests.txt').write_text(test.stdout+test.stderr);assert test.returncode==0,test.stderr
    for name in ['plan.md','study.yaml','executable-protocol.md']:shutil.copy2(OWNER/name,out/name)
    geometry=[]
    for p in sorted((out/'evidence').glob('*-bars.parquet')):
        bars=pd.read_parquet(p);product=bars['product'].iloc[0];q=int(bars.q_i.iloc[0])
        era=np.where(bars.session_date_proxy<'2022-05-02','pre','post') if product=='6S' else np.full(len(bars),'constant')
        for e in sorted(set(era)):
            b=bars[era==e];body=np.abs(b.close_i-b.open_i)/q;span=(b.high_i-b.low_i)/q
            geometry.append({'chart':bars.chart.iloc[0],'era':e,'rows':len(b),'body_q_mean':body.mean(),'body_q_median':body.median(),
              'body_q_min':body.min(),'body_q_max':body.max(),'span_q_mean':span.mean(),'span_q_median':span.median(),'span_q_min':span.min(),'span_q_max':span.max(),
              'duration_seconds_mean':b.duration.mean(),'duration_seconds_median':b.duration.median(),'off_grid_constant':int(b.off_grid_constant.sum()),'off_grid_historical':int(b.off_grid_historical.sum())})
    save_table(out,'input-geometry-unit-eras',geometry)
    shutil.copytree(OWNER,out/'provenance'/'study-source',ignore=shutil.ignore_patterns('__pycache__'))
    numerical={name:sha(OWNER/'src'/name) for name in NUMERICAL}
    cfg=load(out/'config.json');cfg.update(stage='frozen',frozen_at_utc=now());dump(out/'config.json',cfg)
    dump(out/'freeze.json',{'status':'frozen_before_outcomes','utc':now(),'numerical_source_sha256':numerical,
      'config_sha256':sha(out/'config.json'),'dictionary_sha256':sha(out/'feature-dictionary.json'),'plan_sha256':sha(out/'plan.md'),
      'settings_sha256':sha(out/'study.yaml'),'supplement_sha256':sha(out/'executable-protocol.md'),
      'tests':'provenance/pre-freeze-tests.txt','later_outcomes_inspected':False})
    print('Executable protocol frozen before event extraction.',flush=True)

def check_freeze(out):
    frozen=load(out/'freeze.json')
    for n,h in frozen['numerical_source_sha256'].items():assert sha(OWNER/'src'/n)==h,'Frozen numerical code changed: '+n
    for name,key in [('config.json','config_sha256'),('feature-dictionary.json','dictionary_sha256')]:assert sha(out/name)==frozen[key]

def execute(out):
    out=Path(out).resolve();check_freeze(out);assert not (out/'evidence'/'events.parquet').exists()
    primary=[];allrows=[]
    for p in sorted((out/'evidence').glob('*-bars.parquet')):
        bars=pd.read_parquet(p);primary.append(extract(bars));allrows.append(extract(bars,include_repeated=True))
        print('Ledger extracted without later outcome summaries:',p.stem,flush=True)
    df=pd.concat(primary,ignore_index=True);ar=pd.concat(allrows,ignore_index=True)
    df.to_parquet(out/'evidence'/'events.parquet',index=False);ar.to_parquet(out/'evidence'/'events-all-original.parquet',index=False)
    boot=Bootstrap(load(out/'config.json')['observed_session_dates'])
    np.savez_compressed(out/'evidence'/'bootstrap-weights.npz',sessions=np.array(boot.dates),session=boot.weights,block5=boot.blocks)
    lock=select(out,df,boot);print('Selection lock saved. Later evaluation now authorized by frozen configuration.',flush=True)
    evaluate(out,df,boot);print('Frozen later predictions saved.',flush=True)
    summarize(out,df,ar,boot);dump(out/'execution-status.json',{'status':'outcomes_complete','utc':now(),'selection_lock_sha256':sha(out/'selection.lock.json')})
    print('Full numerical evidence and sensitivities complete.',flush=True)

def seal(out):
    out=Path(out).resolve();check_freeze(out);paths=roots();dest=paths.workspace_root/'runs'/STUDY/out.name
    assert load(out/'verification.json')['status']=='pass';assert load(out/'report-verification.json')['status']=='pass'
    assert load(out/'preseal-checks.json')['status']=='pass';assert load(out/'execution-status.json')['status']=='outcomes_complete'
    if dest.exists():raise FileExistsError('Never overwrite completed run')
    retained=(paths.legacy_research_root/'work'/STUDY/out.name).resolve()
    if retained.exists():raise FileExistsError('Retained evidence identity already exists')
    retained.mkdir(parents=True);files=[]
    for p in sorted((out/'evidence').iterdir()):
        shutil.copy2(p,retained/p.name);assert sha(p)==sha(retained/p.name)
        if p.suffix=='.parquet':
            import pyarrow.parquet as pq
            meta=pq.ParquetFile(p);rowcount=meta.metadata.num_rows;schema=str(meta.schema_arrow)
        else:rowcount=None;schema='NumPy compressed arrays: sessions, session[2000,n], block5[2000,n]'
        files.append({'file':p.name,'rows':rowcount,'schema':schema,'sha256':sha(p),'bytes':p.stat().st_size})
    manifest={'study_id':STUDY,'run_id':out.name,'files':files,'retention':'Permanent research evidence; not scratch; retain separately from ordinary Git history',
      'backup':'Local retained and staged copies hash-verified. Off-device backup not performed.'}
    dump(retained/'manifest.json',manifest)
    dump(out/'events.manifest.json',{**manifest,'workspace_relative_locator':str(retained.relative_to(paths.workspace_root)),
      'resolved_locator':str(retained),'retained_manifest_sha256':sha(retained/'manifest.json')})
    shutil.copytree(OWNER,out/'provenance'/'final-study-source',ignore=shutil.ignore_patterns('__pycache__'))
    dest.parent.mkdir(exist_ok=True,parents=True);shutil.copytree(out,dest,ignore=shutil.ignore_patterns('evidence'))
    artifacts={str(p.relative_to(dest)):sha(p) for p in sorted(dest.rglob('*')) if p.is_file()}
    dump(dest/'manifest.json',{'schema_version':'2.0.0','study_id':STUDY,'run_id':out.name,'status':'complete','sealed_at_utc':now(),
      'git_revision':load(out/'provenance'/'environment.json')['git_revision'],'dirty_snapshot':'provenance/initial-tracked-dirty.patch',
      'executed_source':'provenance/study-source','final_source':'provenance/final-study-source','environment_lock':'provenance/uv.lock',
      'settings':'config.json','inputs':'inputs.lock.json','commands':'commands.json','selection':'selection.lock.json','verification':'verification.json',
      'retained_evidence':'events.manifest.json','reports':['report.html','report.md'],'external_publication':False,'profitability_tested':False,'artifacts':artifacts})
    for n,h in artifacts.items():assert sha(dest/n)==h
    dump(out.parent/(out.name+'-seal-verification.json'),{'status':'pass','run':str(dest),'artifacts':len(artifacts),'retained_files':len(files),'manifest_sha256':sha(dest/'manifest.json')})
    print(dest)
