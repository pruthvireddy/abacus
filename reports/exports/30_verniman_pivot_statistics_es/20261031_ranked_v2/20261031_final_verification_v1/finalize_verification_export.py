"""Additive post-seal integrity receipt; never writes into the completed run."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parents[3]
OPS=Path(__file__).resolve().parent
RUN=ROOT/'runs/30_verniman_pivot_statistics_es/20261031_ranked_v2'
EXPORT=ROOT/'reports/exports/30_verniman_pivot_statistics_es/20261031_ranked_v2/20261031_final_verification_v1'
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
manifest=json.loads((RUN/'manifest.json').read_text())
assert manifest['status']=='completed' and manifest['run_id']==RUN.name
for item in manifest['artifacts']:
    if sha(RUN/item['path'])!=item['sha256']:raise ValueError('Sealed artifact changed: '+item['path'])
events=json.loads((RUN/'events.manifest.json').read_text())['artifacts']
for item in events:
    if sha(ROOT/item['path'])!=item['sha256']:raise ValueError('Retained bulk evidence changed')
freeze=json.loads((RUN/'freeze.json').read_text())
for item in freeze['sources']:
    if sha(RUN/item['retained_path'])!=item['sha256']:raise ValueError('Frozen source snapshot changed')
protected=json.loads((OPS/'preserved-baseline-files.json').read_text())
for item in protected:
    if sha(ROOT/item['path'])!=item['sha256']:raise ValueError('Original baseline changed')
records={}
for name in ('seal-v2','narada-source-audit-final-v2','final-priority-transfer-v2'):
    path=OPS/'checks'/(name+'.json');item=json.loads(path.read_text())
    if item['status']!='passed' or item['exit_code']!=0:raise ValueError('Postseal check not passed: '+name)
    if sha(path.with_suffix('.log'))!=item['log_sha256']:raise ValueError('Check log changed')
    records[name]=item
EXPORT.mkdir(parents=True,exist_ok=False)
for name in records:
    for suffix in ('.json','.log'):shutil.copyfile(OPS/'checks'/(name+suffix),EXPORT/(name+suffix))
details=OPS/'checks/final-sealed-priority-transfer-v2.details.json'
shutil.copyfile(details,EXPORT/details.name)
checker_record=records['final-priority-transfer-v2']
for argument in checker_record['argv']:
    path=Path(argument);path=path if path.is_absolute() else ROOT/path
    if path.is_file() and path.is_relative_to(ROOT/'work/ops'):
        shutil.copyfile(path,EXPORT/path.name)
shutil.copyfile(__file__,EXPORT/Path(__file__).name)
mapping=ROOT/'apps/narada/content/release-sources.json'
shutil.copyfile(mapping,EXPORT/'release-sources.snapshot.json')
report={'status':'passed','scope':'Postseal source attribution, exact saved publication transfer and artifact bytes; no additional statistical re-estimation.',
        'run_id':RUN.name,'run_manifest_sha256':sha(RUN/'manifest.json'),
        'sealed_artifact_count':len(manifest['artifacts']),'retained_bulk_artifact_count':len(events),
        'frozen_source_count':len(freeze['sources']),'protected_baseline_files_unchanged':len(protected),
        'full_source_audit':{'publications':105,'hashed_files':3426,'exit_code':records['narada-source-audit-final-v2']['exit_code']},
        'final_priority_transfer':{'reports':2,'file_pins':30,'pngs':8,'csvs':4,'exit_code':checker_record['exit_code']},
        'mapping_sha256':sha(mapping),'details_sha256':sha(details),
        'limits':['Bootstrap intervals not independently re-estimated.','Historical pivot availability and vendor/native-chart parity unverified.','Default workspace gate has two documented missing input prerequisites.','No off-device backup, hosted deployment or trading profitability asserted.']}
(EXPORT/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
source_paths=[RUN/'manifest.json',RUN/'freeze.json',RUN/'scientific-verification.json',RUN/'ranked-verification.json',RUN/'baseline-parity.json',mapping,details]
out={'study_id':'30_verniman_pivot_statistics_es','source_run_id':RUN.name,'revision_id':EXPORT.name,
     'created_at':datetime.now(timezone.utc).isoformat(),'purpose':'Separate final operational verification after sealing; no completed research or publication bytes changed.',
     'command':['python3',str(Path(__file__).resolve().relative_to(ROOT))],'cwd':str(ROOT),'renderer':'standard-library-json/v1',
     'source_artifacts':[{'path':str(p.relative_to(ROOT)),'sha256':sha(p)} for p in source_paths],
     'outputs':[{'path':str(p.relative_to(EXPORT)),'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(EXPORT.iterdir()) if p.is_file()]}
(EXPORT/'manifest.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({'status':'passed','export':str(EXPORT),'verified_sealed_artifacts':len(manifest['artifacts']),'run_manifest_sha256':sha(RUN/'manifest.json')}))
