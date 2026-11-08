#!/usr/bin/env python3
"""Synthetic rejection and lossless-retention checks for the archival adapter."""
import argparse
import copy
import gzip
import hashlib
import importlib.util
import json
import shutil
import sys
import tempfile
from datetime import date
from pathlib import Path
sys.dont_write_bytecode = True


def run(root):
    source = root / 'studies/27_verniman_method_knowledge/capture_retained_daily_maps.py'
    spec = importlib.util.spec_from_file_location('retained_adapter_fixture', source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    original_path = root / 'data/raw/blogspot/verniman/archive_html/20261021T041009Z_2016_review_00a94d4c/collection_manifest.final.json'
    original = json.loads(original_path.read_text())
    html_post = next(x for x in original['posts'] if x['source_format'] == 'archived_html')
    atom_post = next(x for x in original['posts'] if x['source_format'] == 'archived_atom_feed')
    page_post = next(x for x in original['posts'] if x['source_format'] == 'archived_page_post')
    document = {k:copy.deepcopy(original[k]) for k in ['source','requested_start_date','anchor_session_date','chronology_review','collection_completion_review','archive_capture_manifest','collection_review']}
    document.update(posts=[copy.deepcopy(html_post),copy.deepcopy(atom_post),copy.deepcopy(page_post)], files=[], traversal=[], stop_reason='synthetic_selected_fixture')
    checks = {}
    with tempfile.TemporaryDirectory(prefix='daily-map-retained-fixture-') as temp:
        fixture_root = Path(temp)
        def walk(value):
            if isinstance(value, dict):
                if all(k in value for k in ['path','bytes','sha256']):
                    yield value
                for sub in value.values():
                    yield from walk(sub)
            elif isinstance(value,list):
                for sub in value:
                    yield from walk(sub)
        for record in walk(document):
            src = root / record['path']
            dst = fixture_root / record['path']
            dst.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(src,dst)
        manifest = fixture_root/'collection.json'
        manifest.write_text(json.dumps(document))
        sha = hashlib.sha256(manifest.read_bytes()).hexdigest()
        stage=fixture_root/'positive'
        result=module.adapt(fixture_root,stage,manifest,date(2016,1,1),date(2016,12,31),sha,['fixture'])
        out=json.loads((stage/'capture-manifest.json').read_text())
        checks['three_source_formats_retained'] = result['posts']==3 and set(result['source_formats'])=={'archived_html','archived_page_post','archived_atom_feed'}
        checks['dates_descending'] = [p['session_date'] for p in out['posts']]==sorted([p['session_date'] for p in out['posts']],reverse=True)
        for p in out['posts']:
            source_post=next(x for x in document['posts'] if x['url']==p['url'])
            assert 'source_context_excerpt' not in p['year_evidence']
            if 'source_context_excerpt' in source_post['year_evidence']:
                assert p['year_evidence']['source_context_excerpt_identity']['sha256']==hashlib.sha256(source_post['year_evidence']['source_context_excerpt'].encode()).hexdigest()
            payload=gzip.decompress((stage/p['html']['path']).read_bytes())
            if not p['derived_source']:
                assert payload==(fixture_root/source_post['html']['path']).read_bytes()
            else:
                assert source_post['body_html'].encode() in payload
                exact=gzip.decompress((stage/p['original_source']['path']).read_bytes())
                assert exact==(fixture_root/source_post['atom']['path']).read_bytes()
                assert p['source_entry_selector']==source_post['source_entry_selector']
        checks['exact_html_and_complete_original_xml_round_trip']=True
        checks['source_context_prose_kept_in_pinned_source_only']=True
        checks['historical_image_identity_unverified']=all(i['historical_digest_match_verified'] is False and i['source_revision_status']=='current_image_response_historical_bytes_unverified' for p in out['posts'] for i in p['images'])
        checks['no_fresh_network_or_boundary_claim']=out['attempts']==[] and out['lower_boundary_reached'] is False and out['historical_full_year_completeness_claimed'] is False
        def rejection(name, mutation=None, start=date(2016,1,1), pin=None, reuse=False):
            changed=copy.deepcopy(document)
            if mutation: mutation(changed)
            testmanifest=fixture_root/(name+'.json')
            testmanifest.write_text(json.dumps(changed))
            expected=pin if pin is not None else hashlib.sha256(testmanifest.read_bytes()).hexdigest()
            target=stage if reuse else fixture_root/name
            try:
                module.adapt(fixture_root,target,testmanifest,start,date(2016,12,31),expected,['fixture'])
            except (ValueError,FileExistsError):
                checks[name]=True
                if not reuse: assert not target.exists(),name
            else: raise AssertionError(name+' was accepted')
        rejection('manifest_hash_drift_rejected',pin='0'*64)
        rejection('requested_scope_mismatch_rejected',start=date(2016,1,2))
        rejection('atom_selector_drift_rejected',lambda d:d['posts'][1].update(source_entry_selector='tag:missing'))
        rejection('atom_ordinal_drift_rejected',lambda d:d['posts'][1].update(source_feed_entry_ordinal=999))
        rejection('atom_selected_content_drift_rejected',lambda d:d['posts'][1].update(body_html=d['posts'][1]['body_html']+' '))
        rejection('source_title_date_drift_rejected',lambda d:d['posts'][0].update(session_date='2016-01-06'))
        rejection('html_post_id_drift_rejected',lambda d:d['posts'][0].update(source_post_id='999'))
        rejection('homepage_selector_drift_rejected',lambda d:d['posts'][2].update(source_entry_selector='999'))
        rejection('ordered_image_drift_rejected',lambda d:d['posts'][0]['images'].reverse())
        rejection('historical_image_overclaim_rejected',lambda d:d['posts'][0]['images'][0].update(historical_digest_match_verified=True))
        rejection('review_identity_drift_rejected',lambda d:d['chronology_review'].update(sha256='0'*64))
        rejection('existing_stage_refused',reuse=True)
    assert all(checks.values())
    return {'status':'passed','checks':checks,'check_count':len(checks),'temporary_fixture_only':True}

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,default=Path.cwd());args=parser.parse_args()
    print(json.dumps(run(args.root.resolve()),indent=2))
