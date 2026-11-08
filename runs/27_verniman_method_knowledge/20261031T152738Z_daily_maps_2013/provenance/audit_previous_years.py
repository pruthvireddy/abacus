#!/usr/bin/env python3
"""Read-only preservation against the pre-2013 annual archive baseline."""
import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
sys.dont_write_bytecode = True
ROOT = Path('/Users/pruthvi/Documents/projects/abacus')
DEFAULT_STAGE = ROOT / 'work/27_verniman_method_knowledge/20261031T152738Z_daily_maps_2013'


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def verify(base, record):
    path = (base / record['path']).resolve()
    path.relative_to(base.resolve())
    raw = path.read_bytes()
    assert len(raw) == record['bytes'], ('changed length',str(path))
    assert digest(raw) == record['sha256'], ('changed bytes',str(path))
    return path


def capture_records(stage, capture):
    posts = capture['posts'] + capture.get('excluded_context_posts', [])
    records = list(capture.get('attempts', []))
    records += [post['html'] for post in posts if post.get('html')]
    records += [image for post in posts for image in post.get('images', [])]
    records += [post['original_source'] for post in posts if post.get('original_source')]
    if capture.get('current_source_observations'):
        descriptor = capture['current_source_observations']
        verify(stage, descriptor)
        records.append(descriptor)
        records += json.loads((stage / descriptor['path']).read_text()).get('records', [])
    return records


def audit(root, baseline):
    spec = importlib.util.spec_from_file_location('prior_reader_2013',root/'studies/27_verniman_method_knowledge/build_daily_maps.py')
    builder = importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)
    results=[];global_inputs={}
    for prior in baseline:
        manifest_path=root/prior['manifest_path']
        assert digest(manifest_path.read_bytes())==prior['manifest_sha256'], ('run manifest changed',str(manifest_path))
        run=manifest_path.parent
        actual={p.relative_to(run).as_posix() for p in run.rglob('*') if p.is_file()}-{'manifest.json'}
        declared={r['path'] for r in prior['artifacts']}
        assert actual==declared and len(declared)==len(prior['artifacts']),('run inventory changed',str(run))
        for record in prior['artifacts']:verify(run,record)
        stage=root/'work/27_verniman_method_knowledge'/prior['run_id']
        assert (stage/'capture-manifest.json').read_bytes()==(run/'capture-manifest.json').read_bytes(),('capture inventory changed',str(stage))
        assert (stage/'archive/archive-manifest.json').read_bytes()==(run/'payload-inventory.json').read_bytes(),('reader inventory changed',str(stage))
        reader=builder.check(stage)
        capture=json.loads((stage/'capture-manifest.json').read_text());checked=set()
        for record in capture_records(stage,capture):
            if record.get('path') and record['path'] not in checked:
                verify(stage,record);checked.add(record['path'])
        for record in capture.get('retained_inputs',[])+capture.get('retained_source_verifications',[]):
            if not record.get('path'):continue
            identity={k:record[k] for k in ['path','bytes','sha256']}
            existing=global_inputs.get(record['path'])
            assert existing is None or existing==identity,('conflicting original source identity',record['path'])
            if existing is None:verify(root,record);global_inputs[record['path']]=identity
        results.append({'run_id':prior['run_id'],'run_artifacts':len(prior['artifacts']),'reader':reader,'retained_capture_files_checked':len(checked),'status':'unchanged'})
    return {'status':'passed','annual_snapshots':results,'original_source_files_checked':len(global_inputs),'scope':'Read-only exact byte/inventory and presentation preservation; no source-date or scientific revalidation.'}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=ROOT);p.add_argument('--stage',type=Path,default=DEFAULT_STAGE);p.add_argument('--baseline',type=Path)
    a=p.parse_args();b=a.baseline or a.stage/'provenance/prior-annual-preservation.json'
    print(json.dumps(audit(a.root.resolve(),json.loads(b.read_text())),indent=2))
