#!/usr/bin/env python3
"""Independent exact-source and image review of the bounded 2011 recovery."""
import gzip
import hashlib
import importlib.util
import json
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin

sys.dont_write_bytecode = True
ROOT = Path('/Users/pruthvi/Documents/projects/abacus')
REC = ROOT/'work/27_verniman_method_knowledge/20261031T155759Z_daily_maps_2011_recovery'
spec = importlib.util.spec_from_file_location('independent2011bodies', Path('/private/tmp/verniman-2011-audit-capture.py'))
parser = importlib.util.module_from_spec(spec)
spec.loader.exec_module(parser)
checked = {}
def sha(raw): return hashlib.sha256(raw).hexdigest()
def textkey(value): return re.sub(r'\s+', '', value)
def identity(path):
    raw=path.read_bytes()
    return {'path':str(path.relative_to(ROOT)), 'bytes':len(raw), 'sha256':sha(raw)}
def auxiliary_identity(path):
    raw=path.read_bytes()
    return {'original_path':str(path), 'bytes':len(raw), 'sha256':sha(raw)}
def read(record):
    path=(ROOT/record['path']).resolve(); path.relative_to(ROOT)
    raw=path.read_bytes()
    assert len(raw)==record['bytes'] and sha(raw)==record['sha256'], str(path)
    checked[str(path)]=record['sha256']; return raw
class Images(HTMLParser):
    def __init__(self): super().__init__(); self.rows=[]
    def handle_starttag(self,tag,attrs):
        if tag=='img': self.rows.append(dict(attrs))

manifest_record=identity(REC/'recovery-manifest.json')
assert manifest_record['sha256']=='24cd449faeee26a091b9e06de07a6c40ef47714a2c40dc183d7d58e3e0696c82'
manifest=json.loads(read(manifest_record))
assert manifest['requested_start_date']=='2011-01-01' and manifest['anchor_session_date']=='2011-12-31'
assert manifest['image_capture_status']=='completed' and len(manifest['files'])==311
for record in manifest['files']: read(record)
posts=manifest['posts']; assert len(posts)==70
assert Counter(p['source_format'] for p in posts)=={'archived_html':17,'archived_atom_feed':50,'current_html':3}

# Search every already frozen later annual collection using complete nonempty bodies.
# Empty strings cannot establish source identity, including image-only posts.
later=defaultdict(list); frozen=[]
baseline_path=Path('/private/tmp/verniman-2011-preservation-20261031T155759Z.json')
baseline=json.loads(baseline_path.read_text()); assert len(baseline)==15
for previous in baseline:
    run=ROOT/previous['manifest_path']; assert sha(run.read_bytes())==previous['manifest_sha256']
    reader=ROOT/'work/27_verniman_method_knowledge'/previous['run_id']/'archive'
    inventory_record=identity(reader/'archive-manifest.json')
    assert read(inventory_record)==(run.parent/'payload-inventory.json').read_bytes()
    inventory=json.loads(read(inventory_record)); by_path={r['path']:r for r in inventory['files']}
    frozen.append({'run_id':previous['run_id'],'sealed_manifest':{'path':previous['manifest_path'],'sha256':previous['manifest_sha256']},'reader_inventory':inventory_record})
    for item in inventory['posts']:
        relative=item['capsule']+'/article.json.gz'
        record=by_path[relative]; absolute={**record,'path':str((reader/relative).relative_to(ROOT))}
        data=json.loads(gzip.decompress(read(absolute))); key=textkey(data['full_text'])
        if key:
            later[sha(key.encode())].append({'session_date':data['session_date'],'title':data['title'],'reader_capsule':item['capsule'],'article_metadata':absolute})
assert sum(map(len,later.values()))==2419

reviewed_path=Path('/private/tmp/verniman-2011-reviewed-context-identities.json')
reviewed=set(tuple(r) for r in json.loads(reviewed_path.read_text()))
assert len(reviewed)==54
contexts=[]; failures=[]; matches=[]; image_hashes=set(); pairs=set(); missing_urls=set()
raw_images=retained=missing=inline=body_count=0
feed_revisions=defaultdict(list); tracking=[]
ns={'a':'http://www.w3.org/2005/Atom'}
for ordinal,post in enumerate(posts,1):
    assert not post.get('capture_failed'), 'Unexpected failure requires independent review'
    fmt=post['source_format']; image_attrs=[]
    if fmt=='archived_atom_feed':
        original=read(post['atom']); body=parser.atom_source(original,post); bodies=[body]
        tree=ET.fromstring(original); entries=tree.findall('a:entry',ns)
        assert len(entries)==25
        entry=entries[post['source_feed_entry_ordinal']-1]
        assert entry.findtext('a:id',namespaces=ns)==post['source_entry_selector']==post['source_entry_id']
        assert post['source_post_id']==post['source_entry_selector'].rsplit('post-',1)[1]
        assert post['source_published_at']==entry.findtext('a:published',namespaces=ns)
        assert post['source_updated_at']==entry.findtext('a:updated',namespaces=ns)
        authored=entry.findtext('a:content',default='',namespaces=ns)
        assert post['body_html']==authored
        q=Images(); q.feed(authored); image_attrs=q.rows
        assert textkey(''.join(body['parts']))==textkey(post['body_text'])
        read(post['entry_record'])
    else:
        original=read(post['html']); q=parser.Bodies();q.feed(original.decode('utf-8','replace')); bodies=q.rows
        assert len(bodies)==post['post_body_count']
        assert textkey(''.join(''.join(b['parts']) for b in bodies))==textkey(post['body_text'])
    read(post['post_record'])
    if fmt=='current_html':
        assert post['role']=='excluded_current_context' and post['session_date'] is None
        assert all(k not in post for k in ['archive_url','archive_timestamp','archive_observed_at','year_evidence'])
        assert post['html']['capture_kind']=='current_observation' and post['html']['http_status']==200
    elements=[(b,im) for b in bodies for im in b['images']]
    assert len(elements)==len(post['actual_image_elements'])==len(post['images'])
    for index,((body,element),declared,saved) in enumerate(zip(elements,post['actual_image_elements'],post['images'])):
        inline_url=urljoin(post['url'],element['inline']); linked_url=urljoin(post['url'],element['linked']) if element['linked'] else inline_url
        preferred=linked_url if re.search(r'(?:blogger\.googleusercontent\.com|bp\.blogspot\.com)/',linked_url) else inline_url
        assert declared['url']==preferred and declared['inline_url']==inline_url
        assert saved['original_image_url']==preferred and saved['historical_digest_match_verified'] is False
        raw_images+=1
        if saved['kind']=='missing_source_image':
            assert fmt=='archived_atom_feed' and saved.get('error') and not saved.get('path')
            attrs=image_attrs[index]
            assert attrs['src']==preferred and '/tracker/' in preferred and attrs['width']=='1' and attrs['height']=='1'
            assert len(saved['attempts'])==1 and saved['attempts'][0]['http_status']==404
            for attempt in saved['attempts']:read(attempt)
            missing+=1; missing_urls.add(preferred)
            tracking.append({'source_ordinal':ordinal,'entry_selector':post['source_entry_selector'],'entry_ordinal':post['source_feed_entry_ordinal'],'url':preferred,'width':1,'height':1})
        else:
            assert saved['kind']=='current_source_image_fallback'
            assert saved['url']==(inline_url if saved.get('rendition')=='inline_thumbnail' else preferred)
            if saved.get('rendition')=='inline_thumbnail':assert saved.get('full_size_error'); inline+=1
            read(saved); image_hashes.add(saved['sha256']);pairs.add((preferred,inline_url));retained+=1
    summaries=[]
    for body in bodies:
        title=' '.join(body['title'].split()); key=textkey(''.join(body['parts'])); digest=sha(key.encode())
        assert (body['id'],title,digest) in reviewed, ('Unreviewed source body',ordinal,title,digest)
        record={'source_post_id':body['id'],'title':title,'normalized_body_sha256':digest,'image_elements':len(body['images']),'ordered_body_links_sha256':sha(json.dumps(body['links'],ensure_ascii=False,separators=(',',':')).encode())}
        if key and digest in later:
            assert len(later[digest])==1 and later[digest][0]['session_date'].startswith('2022-')
            record['exclusion_reason']='Complete nonempty actual body exactly matches a frozen 2022 morning plan; locator year is not source-year proof.'
            record['exact_frozen_later_year_matches']=later[digest]
            matches.append({'source_ordinal':ordinal,**record})
        elif title=='Trading Update':
            assert not key and len(body['images']) in {3,4}
            record['exclusion_reason']='Visual review: three historical ABCD/Pullback execution-example charts, with an additional 1x1 tracker in Atom only; no prospective 2011 morning-plan session established.'
        elif title in {'Dollar-Bonds-Stocks','Euro-Gold-Crude','Markets Projection'}:
            assert not key
            record['exclusion_reason']='Visual review: broad weekly support/resistance or multi-year monthly projection charts; no prospective morning-plan session established.'
        elif fmt=='current_html':
            record['exclusion_reason']='Current-only general educational observation from an official-sitemap locator; not evidence of historical 2011 content.'
        else:
            record['exclusion_reason']='Actual complete body is general method, motivational, intraday execution example, or older 2010 recap context; no supported prospective 2011 morning plan.'
        summaries.append(record);body_count+=1
        if fmt=='archived_atom_feed':
            feed_revisions[body['id']].append({'ordinal':ordinal,'title':title,'normalized_body_sha256':digest,'ordered_body_links_sha256':record['ordered_body_links_sha256'],'actual_image_elements':post['actual_image_elements'],'original_source':post['atom'],'entry_selector':post['source_entry_selector'],'entry_ordinal':post['source_feed_entry_ordinal']})
    contexts.append({'ordinal':ordinal,'title':post['title'],'url':post['url'],'archive_url':post.get('archive_url'),'source_format':fmt,'source_html':post.get('html'),'source_atom':post.get('atom'),'source_post_record':post['post_record'],'body_count':len(bodies),'body_reviews':summaries,'actual_image_elements':len(elements),'exclusion_reason':'No in-scope 2011 morning plan established; complete raw context and all image outcomes retained.' if summaries else 'Observed index contains zero article bodies; no daily source inferred.'})
assert body_count==73 and len(contexts)==70 and len(matches)==3
assert (raw_images,retained,len(pairs),len(image_hashes),missing,len(missing_urls),inline)==(131,81,59,58,50,38,0)
assert len(feed_revisions)==38 and sum(len(v)>1 for v in feed_revisions.values())==12
visual_index=Path('/private/tmp/verniman-2011-visual-image-index.json')
vis=json.loads(visual_index.read_text());assert len(vis)==58 and {sha((ROOT/v['path']).read_bytes()) for v in vis}==image_hashes
sitemap_path=Path('/private/tmp/verniman-2011-sitemap-precheck-result.json');sitemap=json.loads(sitemap_path.read_text());assert sitemap['status']=='passed'
result={'status':'passed','scope':'Independent complete actual-body classification, exact Atom selector/ordinal and original publication checks, all raw image identities/outcomes and visual review; empty selection does not establish historical absence.',
 'recovery_manifest':manifest_record,'checked_unique_files':len(checked),'raw_source_revisions':70,'actual_post_body_instances':body_count,'successfully_captured_sources':70,'failed_indexed_locators':0,'capture_failures':[],
 'selected_records':0,'dated':0,'undated':0,'image_references':0,'unique_image_hashes':0,'selected_source_ids':[],'overlaps':[],
 'raw_source_formats':dict(Counter(p['source_format'] for p in posts)),'excluded_context_records':70,'excluded_archived_context_records':67,'excluded_current_context_records':3,
 'multi_body_context_records':sum(c['body_count']>1 for c in contexts),'single_body_context_records':sum(c['body_count']==1 for c in contexts),'zero_body_context_records':sum(c['body_count']==0 for c in contexts),
 'raw_image_references':raw_images,'retained_raw_image_references':retained,'successful_raw_image_pairs':len(pairs),'unique_retained_raw_images':len(image_hashes),'raw_missing_images':missing,'unique_missing_image_urls':len(missing_urls),'missing_tracking_pixel_references':missing,'missing_authored_chart_references':0,'raw_inline_fallbacks':inline,
 'exact_later_year_full_body_matches':matches,'frozen_later_year_inventories':frozen,'frozen_later_year_nonempty_body_references':2419,'frozen_preservation_baseline':auxiliary_identity(baseline_path),
 'retained_sitemap_precheck':auxiliary_identity(sitemap_path),'reviewed_context_identity_file':auxiliary_identity(reviewed_path),'visually_reviewed_image_payloads':auxiliary_identity(visual_index),'tracking_pixel_reviews':tracking,
 'atom_entry_records':50,'atom_unique_ids':38,'atom_repeated_ids':12,'atom_overlap_revisions':{k:v for k,v in feed_revisions.items() if len(v)>1},
 'excluded_contexts':contexts,'lower_boundary_observed':False,'historical_full_year_completeness_claimed':False}
print(json.dumps(result,indent=2))
