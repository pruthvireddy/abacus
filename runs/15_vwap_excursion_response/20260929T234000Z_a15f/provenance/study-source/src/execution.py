"""Staged deterministic execution, frozen-source checks, and provenance."""
from __future__ import annotations
import importlib.metadata
import json
import platform
import shutil
import subprocess
from pathlib import Path
import pandas as pd
from .common import OWNER, STUDY, SESSIONS, sha, dump, save_table, utcnow, week
from .inputs import roots, verify_inputs, feature_parts, load_year
from .engine import make_session, episodes, horizons


def check_freeze():
    freeze=json.loads((OWNER/'freeze.json').read_text())
    for path,digest in freeze['frozen_files'].items():
        if sha(OWNER/path)!=digest:raise ValueError(f'Frozen executable changed: {path}')
    return freeze


def execute(out,pilot):
    freeze=check_freeze();out=Path(out);out.mkdir(parents=True,exist_ok=False)
    (out/'evidence').mkdir();(out/'provenance').mkdir();(out/'tables').mkdir()
    pilot=Path(pilot)
    assert sha(pilot/'pilot.json')==freeze['pilot_sha256']
    assert json.loads((pilot/'pilot.json').read_text())['status']=='pass'
    dump(out/'execution-status.json',{'status':'running','started_at':utcnow()})
    verify_inputs(out)
    for name in ['inputs.lock.json','study.yaml','protocol-1.0.0.md','protocol-1.0.0.json','freeze.json','report-schema.json','plan.md']:
        shutil.copy2(OWNER/name,out/name)
    shutil.copy2(OWNER/'protocol-1.0.0.json',out/'config.json')
    shutil.copytree(pilot,out/'pilot')
    for f in pilot.joinpath('tables').glob('release-coverage.*'):shutil.copy2(f,out/'tables'/f.name)
    for folder in ['src','tests']:
        shutil.copytree(OWNER/folder,out/'provenance/study-source'/folder,ignore=shutil.ignore_patterns('__pycache__'))
    for f in OWNER.glob('*.py'):shutil.copy2(f,out/'provenance/study-source'/f.name)
    root=roots().workspace_root
    for file in ['uv.lock','pyproject.toml','packages/bhishma/src/abacus_bhishma/feature_loader.py',
       'packages/bhishma/src/abacus_bhishma/continuous_loader.py','packages/bhishma/src/abacus_bhishma/paths.py']:
        dest=out/'provenance'/file;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(root/file,dest)
    (out/'provenance/git-status.txt').write_text(subprocess.check_output(['git','status','--short'],cwd=root,text=True))
    (out/'provenance/dirty-tracked.patch').write_bytes(subprocess.check_output(['git','diff','HEAD','--'],cwd=root))
    dump(out/'provenance/environment.json',{'python':platform.python_version(),'platform':platform.platform(),
       'packages':dict(sorted((d.metadata['Name'],d.version) for d in importlib.metadata.distributions() if d.metadata['Name'])),
       'uv_lock_sha256':sha(root/'uv.lock'),'git_revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),
       'command_mode':'existing locked workspace environment; uv --locked --no-sync'})
    counts={};all_weeks=set()
    # Independent product/year pieces bound memory and identify partial failures.
    for product,year in feature_parts():
        f,r=load_year(product,year);rawdays=dict(tuple(r.groupby('session_date',sort=False)))
        buckets={name:[] for name in ['parents','thresholds','touches','candidates','departure-horizons','touch-horizons']}
        for day,features in f.groupby('session_date',sort=True):
            all_weeks.add(week(day))
            for name in SESSIONS:
                s=make_session(features,rawdays[day],product,name,day)
                p,e,t,c=episodes(s)
                for key,rows in [('parents',p),('thresholds',e),('touches',t),('candidates',c)]:buckets[key].extend(rows)
                for ev in e:buckets['departure-horizons'].extend(horizons(s,ev))
                for ev in t:buckets['touch-horizons'].extend(horizons(s,ev))
        part=out/f'evidence/parts/{product}-{year}';part.mkdir(parents=True)
        for key,rows in buckets.items():
            frame=pd.DataFrame(rows)
            frame.to_parquet(part/f'{key}.parquet',index=False)
            counts[key]=counts.get(key,0)+len(frame)
        print(f'executed {product} {year}: {len(buckets["parents"])} parents; partition saved',flush=True)
    for key in counts:
        files=sorted((out/'evidence/parts').glob(f'*/{key}.parquet'))
        frames=[pd.read_parquet(f) for f in files]
        frame=pd.concat([f for f in frames if len(f)],ignore_index=True)
        frame.to_parquet(out/f'evidence/{key}.parquet',index=False)
        frame.to_csv(out/f'evidence/{key}.csv.gz',index=False,compression={'method':'gzip','mtime':0})
    dump(out/'tables/week-universe.json',sorted(all_weeks))
    dump(out/'execution-status.json',{'status':'outcomes_complete','finished_at':utcnow(),'counts':counts,
       'protocol_frozen_at':freeze['frozen_at'],'protocol_sha256':sha(out/'config.json')})
    return counts
