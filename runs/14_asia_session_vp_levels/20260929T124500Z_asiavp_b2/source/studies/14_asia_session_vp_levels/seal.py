"""Seal a verified study-14 staging directory into an immutable local run."""
from __future__ import annotations

import argparse
from datetime import datetime,timezone
import importlib.metadata
import json
from pathlib import Path
import shutil
import subprocess
import sys

from abacus_bhishma.paths import load_workspace_paths
from abacus_bhishma.vp_hvn_release import sha256,dump
from verify_run import verify


def seal(stage):
    paths=load_workspace_paths();workspace=paths.workspace_root;root=paths.publication_root
    study=workspace/'studies/14_asia_session_vp_levels'
    stage=stage.resolve()
    if stage.parent != (workspace/'work/14_asia_session_vp_levels').resolve():
        raise ValueError('stage must be directly under this study work directory')
    destination=workspace/'runs/14_asia_session_vp_levels'/stage.name
    if destination.exists():raise FileExistsError(destination)
    checks=verify(stage)
    lock=json.loads((study/'inputs.lock.json').read_text())
    feature=lock['derived_feature_release']
    if sha256(root/feature['manifest_path'])!=feature['sha256']:
        raise ValueError('pinned feature release changed')
    sources=[study/name for name in ('run.py','render_results.py','verify_run.py','seal.py','plan.md',
             'protocol-1.0.0.md','protocol-features-1.0.0.md','study.yaml','inputs.lock.json',
             'reference/vp_hvn_levels_dev.pine')]
    sources.extend(sorted((study/'src').glob('*.py')))
    sources.extend(sorted((study/'tests').glob('*.py')))
    sources.append(workspace/'uv.lock')
    records=[]
    for source in sources:
        relative=source.relative_to(workspace)
        target=stage/'source'/relative;target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(source,target)
        records.append({'path':str(relative),'sha256':sha256(source)})
    prior=workspace/'work/14_asia_session_vp_levels/20260927T180756Z_preparation_2281/tables/quality_by_year.csv'
    quality_identity={'preparation_quality_table':str(prior.relative_to(workspace)),
                      'sha256':sha256(prior)}
    if sha256(stage/'tables/quality_by_year.csv')!=quality_identity['sha256']:
        raise ValueError('copied quality table changed')
    artifacts=[{'path':str(p.relative_to(stage)),'sha256':sha256(p),'bytes':p.stat().st_size}
               for p in sorted(stage.rglob('*')) if p.is_file() and p.name!='manifest.json']
    commands=[
        f'UV_CACHE_DIR=work/.uv-cache ./scripts/uv run --locked --no-sync python studies/14_asia_session_vp_levels/run.py --execute --stage work/14_asia_session_vp_levels/{stage.name}',
        f'UV_CACHE_DIR=work/.uv-cache ./scripts/uv run --locked --no-sync python studies/14_asia_session_vp_levels/run.py --add-sensitivities --stage work/14_asia_session_vp_levels/{stage.name}',
        f'UV_CACHE_DIR=work/.uv-cache ./scripts/uv run --locked --no-sync python studies/14_asia_session_vp_levels/render_results.py --stage work/14_asia_session_vp_levels/{stage.name}',
        f'UV_CACHE_DIR=work/.uv-cache ./scripts/uv run --locked --no-sync python studies/14_asia_session_vp_levels/verify_run.py --stage work/14_asia_session_vp_levels/{stage.name}',
    ]
    manifest={'study_id':'14_asia_session_vp_levels','run_id':stage.name,'status':'sealed_local_evidence',
              'created_utc':datetime.now(timezone.utc).isoformat(),
              'commands':commands,'checks':checks,
              'git_revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=workspace,text=True).strip(),
              'git_status_at_seal':subprocess.check_output(['git','status','--porcelain'],cwd=workspace,text=True),
              'python':sys.version,'environment':{n:importlib.metadata.version(n) for n in ('numpy','pandas','pyarrow')},
              'uv_lock_sha256':sha256(workspace/'uv.lock'),
              'protocol_sha256':sha256(study/'protocol-1.0.0.md'),
              'feature_manifest':feature,'quality_preparation_source':quality_identity,
              'source_snapshot':records,'artifacts':artifacts,
              'template_version':'abacus-report-1',
              'limitation':'One-minute OHLCV, retrospective adjusted-coordinate sensitivity, no external TradingView tick parity or fill certification.'}
    dump(stage/'manifest.json',manifest)
    destination.parent.mkdir(parents=True,exist_ok=True)
    shutil.copytree(stage,destination)
    for item in artifacts:
        if sha256(destination/item['path'])!=item['sha256']:
            raise ValueError(f"sealed artifact mismatch: {item['path']}")
    if sha256(destination/'manifest.json')!=sha256(stage/'manifest.json'):
        raise ValueError('sealed manifest mismatch')
    return destination


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage',type=Path,required=True)
    args=parser.parse_args()
    print(seal(args.stage))
