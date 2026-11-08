#!/usr/bin/env python3
"""Synthetic full/inline/missing image provenance roundtrip against real helpers."""
import base64,copy,gzip,hashlib,importlib.util,json,sys,tempfile
from datetime import date
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path('/Users/pruthvi/Documents/projects/abacus')


def run(root):
    spec=importlib.util.spec_from_file_location('image_guard_adapter2015',root/'studies/27_verniman_method_knowledge/capture_retained_daily_maps.py')
    adapter=importlib.util.module_from_spec(spec);spec.loader.exec_module(adapter)
    spec=importlib.util.spec_from_file_location('image_guard_builder2015',root/'studies/27_verniman_method_knowledge/build_daily_maps.py')
    builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)
    results={}
    with tempfile.TemporaryDirectory(prefix='daily-map-2015-image-guards-') as temp:
        base=Path(temp)
        def write(relative,raw):
            p=base/relative;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
            return {'path':relative,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
        review=write('input/review.json',b'{"kind":"synthetic2015review","status":"passed"}\n')
        png=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a34kAAAAASUVORK5CYII=')
        full=[f'https://1.bp.blogspot.com/s1600/source-{i}.png' for i in range(1,4)]
        inline=[f'https://1.bp.blogspot.com/s400/source-{i}.png' for i in range(1,4)]
        html=('<a name="12345"></a><h3 class="post-title">Outlook 05/13</h3><div class="post-body"><p>Explicit synthetic opening plan text.</p>'+''.join(f'<a href="{a}"><img src="{b}"></a>' for a,b in zip(full,inline))+'</div>').encode()
        hr=write('input/source.html',html);pr=write('input/post.json',b'{"source_post_id":"12345"}')
        def image_record(i,url):
            record=write(f'input/image-{i}.png',png)
            return {**record,'kind':'current_source_image_fallback','url':url,'original_image_url':full[i-1],'headers':{'Content-Type':'image/png'},'source_revision_status':'current_image_response_historical_bytes_unverified','historical_digest_match_verified':False,'captured_at':'2026-10-31T00:00:00Z'}
        images=[image_record(1,full[0]),image_record(2,inline[1]),{'kind':'missing_source_image','url':full[2],'original_image_url':full[2],'error':'Both original linked and inline source URLs were unavailable.'}]
        images[1].update(rendition='inline_thumbnail',full_size_error='HTTP404 for actual full-size source URL')
        post={'url':'https://verniman.blogspot.com/2015/fixture.html','title':'Outlook 05/13','session_date':'2015-05-13','html':hr,'post_record':pr,'source_post_id':'12345','source_format':'archived_html','session_date_method':'synthetic_explicit_review','session_date_source_text':'Outlook 05/13','images':images,'date_warnings':[],'year_evidence':{'year':2015,'method':'synthetic_independent_year_review'},'reviewed_daily_plan':True,'date_review':{'status':'dated_title','source_title':'Outlook 05/13'},'captured_at':'2026-10-31T00:00:00Z','archive_observed_at':'2015-05-13T20:00:00Z','archive_url':'https://web.archive.org/web/20150513200000id_/http://verniman.blogspot.com/2015/fixture.html'}
        doc={'source':'verniman','requested_start_date':'2015-01-01','anchor_session_date':'2015-12-31','posts':[post],'files':[],'traversal':[],'chronology_review':review,'collection_completion_review':review,'archive_capture_manifest':review,'stop_reason':'synthetic_fixture_only'}
        def prepare(document):
            rec=write('input/collection.json',json.dumps(document).encode())
            return adapter.Adapter(base).prepare(base/rec['path'],date(2015,1,1),date(2015,12,31),rec['sha256'])
        _,prepared=prepare(doc);assert len(prepared[0][3])==3;results['full_inline_and_missing_source_elements_accepted']=True
        def reject(name,change):
            changed=copy.deepcopy(doc);change(changed['posts'][0]);
            try:prepare(changed)
            except (ValueError,TypeError):results[name]=True
            else:raise AssertionError('forbidden image case accepted: '+name)
        reject('inline_url_must_be_actual_source',lambda p:p['images'][1].update(url='https://1.bp.blogspot.com/s400/guessed.png'))
        reject('inline_requires_full_failure',lambda p:p['images'][1].pop('full_size_error'))
        reject('inline_requires_reviewed_daily_plan',lambda p:p.update(reviewed_daily_plan=False))
        reject('missing_record_may_not_invent_payload_path',lambda p:p['images'][2].update(path='input/image-1.png'))
        reject('missing_record_requires_explicit_error',lambda p:p['images'][2].pop('error'))
        reject('original_full_image_identity_must_match',lambda p:p['images'][1].update(original_image_url=full[0]))
        reject('historical_digest_overclaim_rejected',lambda p:p['images'][0].update(historical_digest_match_verified=True))
        reject('actual_image_elements_cannot_be_omitted',lambda p:p['images'].pop())
        prepare(doc)
        stage=base/'output';result=adapter.adapt(base,stage,base/'input/collection.json',date(2015,1,1),date(2015,12,31),None)
        cm=json.loads((stage/'capture-manifest.json').read_text());ims=cm['posts'][0]['images']
        assert len(ims)==3 and ims[0]['url']==full[0] and ims[1]['url']==inline[1] and ims[1]['requested_url']==full[1]
        assert ims[1]['rendition']=='inline_thumbnail' and ims[1]['full_size_error']
        assert ims[2]['kind']=='missing_source_image' and not ims[2].get('path') and ims[2]['error']
        for item in ims[:2]:assert (stage/item['path']).read_bytes()==png
        results['capture_roundtrip_keeps_exact_inline_bytes_and_missing_record']=True
        builder.build(stage);metrics=json.loads((stage/'archive/metrics.json').read_text())
        assert metrics['image_references']==3 and metrics['retained_image_references']==2 and metrics['missing_image_references']==1 and metrics['inline_rendition_references']==1
        view=(stage/'archive/2015/05/13/index.html').read_text()
        assert view.count('Image unavailable.')==1 and view.count('<figure>')==2
        assert 'historical image bytes unverified' in view
        assert 'Inline rendition retained; full-size source unavailable.' in view
        results['both_inline_and_historical_uncertainty_captions_visible']=True
        assert 'Both original linked and inline source URLs were unavailable.' in (stage/'archive/gap-log.md').read_text()
        results['reader_retains_source_count_and_visible_missing_image_notice']=True
    assert all(results.values())
    return {'status':'passed','scope':'Synthetic source-image provenance guards and reader roundtrip only.','checks':results,'check_count':len(results)}


if __name__=='__main__':print(json.dumps(run(ROOT),indent=2))
