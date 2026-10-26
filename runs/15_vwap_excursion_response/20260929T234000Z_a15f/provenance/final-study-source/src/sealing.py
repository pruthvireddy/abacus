"""One-way sealing into a new run and retained (non-scratch) event storage."""
from __future__ import annotations
import json
import shutil
import subprocess
from pathlib import Path
import pandas as pd
from .common import OWNER,STUDY,sha,dump,utcnow
from .inputs import roots
from .execution import check_freeze


def seal(out):
    out=Path(out).resolve();paths=roots();run_id=out.name;dest=paths.workspace_root/'runs'/STUDY/run_id
    if dest.exists():raise FileExistsError(f'Never replace a completed run: {dest}')
    check_freeze()
    for name in ['verification.json','uncertainty-verification.json','report-verification.json','visual-inspection.json','preseal-checks.json']:
        r=json.loads((out/name).read_text());assert r['status']=='pass',name
    assert json.loads((out/'execution-status.json').read_text())['status']=='outcomes_complete'
    # Resolve the historically retained evidence root via the configured compatibility link.
    if paths.legacy_research_root is None:raise ValueError('Configure legacy_research_root for retained Sahadeva evidence')
    retained=(paths.legacy_research_root/'work'/STUDY/run_id).resolve()
    if retained.exists():raise FileExistsError(f'Retained identity already exists: {retained}')
    retained.mkdir(parents=True)
    files=[]
    for src in sorted((out/'evidence').iterdir()):
        if not src.is_file():continue
        target=retained/src.name;shutil.copy2(src,target);assert sha(src)==sha(target)
        base=src.name.split('.')[0]
        row_count=len(pd.read_parquet(out/'evidence'/f'{base}.parquet'))
        files.append({'file':src.name,'rows':row_count,'bytes':target.stat().st_size,'sha256':sha(target),
                     'schema_version':'1.0.0','format':'parquet' if src.suffix=='.parquet' else 'csv.gz'})
    retained_manifest={'study_id':STUDY,'run_id':run_id,'created_at':utcnow(),'files':files,
       'retention':'Permanent research evidence; preserve independently of work/ cleanup. No automatic deletion.',
       'backup_status':'Local retained copy verified. Staged copy also remains. No off-device backup was performed or verified.'}
    dump(retained/'manifest.json',retained_manifest)
    try:locator=str(retained.relative_to(paths.workspace_root))
    except ValueError:locator=str(retained)
    dump(out/'events.manifest.json',{'schema_version':'1.0.0','study_id':STUDY,'run_id':run_id,
       'storage_configuration':'legacy_research_root/work/<study>/<run> resolved through Abacus configuration',
       'workspace_relative_locator':locator,'resolved_locator_at_seal':str(retained),
       'retained_manifest_sha256':sha(retained/'manifest.json'),'files':files,
       'retention':retained_manifest['retention'],'backup_status':retained_manifest['backup_status'],
       'foreign_keys':{'thresholds.parent_id':'parents.parent_id','touches.parent_id':'parents.parent_id',
        'departure-horizons.event_id':'thresholds.event_id','touch-horizons.event_id':'touches.event_id'},
       'column_semantics':'UTC timestamps; raw price points; *_ticks min ticks; *_sigma frozen event sigma; nullable forward outcomes. See config/protocol and report schema.'})
    # Include final renderer/audit/sealer source in addition to the pre-execution numerical snapshot.
    shutil.copytree(OWNER,out/'provenance/final-study-source',ignore=shutil.ignore_patterns('__pycache__'),dirs_exist_ok=True)
    shutil.copy2(OWNER/'pre-freeze-tests.txt',out/'provenance/pre-freeze-tests.txt')
    shutil.copy2(out.parent/'preservation-baseline.json',out/'provenance/preservation-baseline.json')
    logs=out/'provenance/commands';logs.mkdir(exist_ok=True)
    for src in out.parent.glob(run_id+'-*.log'):shutil.copy2(src,logs/src.name)
    for src in out.parent.glob('pilot_*.log'):shutil.copy2(src,logs/src.name)
    # Verification is numerical; browser display restrictions are a separate recorded limit.
    verified=json.loads((out/'verification.json').read_text())
    verified['additional_checks']=['independent 120 bootstrap intervals','five report structural/value checks','144 SVG figures visually reviewed','preseal docs and synthetic tests']
    verified['remaining_checks']=[]
    verified['browser_layout_verified']=False
    verified['browser_layout_limitation']='file:// disallowed by browser policy; static figures and report tables checked offline.'
    verified['postseal_navigation_record']=f'studies/{STUDY}/completion-verification.json'
    dump(out/'verification.json',verified)
    # Reports/small tables/provenance are the sealed bundle; bulk ledgers have retained locators.
    dest.parent.mkdir(parents=True,exist_ok=True)
    shutil.copytree(out,dest,ignore=shutil.ignore_patterns('evidence'))
    artifacts={str(p.relative_to(dest)):sha(p) for p in sorted(dest.rglob('*')) if p.is_file()}
    manifest={'schema_version':'1.0.0','study_id':STUDY,'run_id':run_id,'status':'complete','sealed_at':utcnow(),
       'command_manifest':'commands.json','git_revision':json.loads((out/'provenance/environment.json').read_text())['git_revision'],
       'dirty_source_snapshot':'provenance/study-source','final_source_snapshot':'provenance/final-study-source',
       'environment_lock':'provenance/uv.lock','input_lock':'inputs.lock.json','protocol':'protocol-1.0.0.json',
       'freeze_record':'freeze.json','verification':'verification.json','retained_events':'events.manifest.json',
       'numerical_authority':'tables/summary.parquet','reports':['report.html','asia.html','london.html','ny.html','globex.html'],
       'external_publication':False,'profitability_tested':False,'artifacts':artifacts,
       'postseal_navigation_record':f'studies/{STUDY}/completion-verification.json'}
    dump(dest/'manifest.json',manifest)
    for file,digest in artifacts.items():assert sha(dest/file)==digest
    dump(out.parent/(run_id+'-seal-verification.json'),{'status':'pass','verified_at':utcnow(),'run':str(dest),
       'manifest_sha256':sha(dest/'manifest.json'),'artifacts_verified':len(artifacts),'retained_files_verified':len(files),
       'retained_locator':str(retained),'retained_manifest_sha256':sha(retained/'manifest.json')})
    print(dest)
