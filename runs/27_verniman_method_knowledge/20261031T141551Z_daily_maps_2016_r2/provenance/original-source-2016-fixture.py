"""Exercise derived Atom wrapper provenance, original XML retention and image qualification."""
import gzip,hashlib,importlib.util,json,tempfile,sys
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path('/Users/pruthvi/Documents/projects/abacus')
spec=importlib.util.spec_from_file_location('fixture_2016_original',ROOT/'studies/27_verniman_method_knowledge/build_daily_maps.py');b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
def rec(path,raw,**extra):return {'path':path,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),**extra}
with tempfile.TemporaryDirectory(prefix='daily-map-original-2016-') as tmp:
 s=Path(tmp);(s/'captures').mkdir();(s/'assets').mkdir()
 xml=b'<feed xmlns="http://www.w3.org/2005/Atom"><entry><id>first</id><title>Outlook 01/05</title></entry><entry><id>second</id><title>Outlook 02/29</title></entry></feed>'
 gz=gzip.compress(xml,mtime=0);(s/'captures/feed.xml.gz').write_bytes(gz);original=rec('captures/feed.xml.gz',gz,uncompressed_sha256=hashlib.sha256(xml).hexdigest(),uncompressed_bytes=len(xml))
 image=b'fixture original compressed image bytes';(s/'assets/source.png').write_bytes(image)
 posts=[]
 for i,(date,entry) in enumerate([('2016-01-05','first'),('2016-02-29','second')],1):
  title='Outlook '+date[5:].replace('-','/');url=f'https://verniman.blogspot.com/2016/fixture-{i}.html';full=f'https://1.bp.blogspot.com/source/s1600/{i}.png';inline=f'https://1.bp.blogspot.com/source/s400/{i}.png'
  raw=f'<h3 class="post-title">{title}</h3><div class="post-body"><a href="{full}"><img src="{inline}"></a><p>Exact selected entry text {entry}.</p></div>'.encode();compressed=gzip.compress(raw,mtime=0);path=f'captures/wrapper-{i}.html.gz';(s/path).write_bytes(compressed)
  posts.append({'url':url,'session_date':date,'title':title,'html':rec(path,compressed,uncompressed_sha256=hashlib.sha256(raw).hexdigest()),'images':[rec('assets/source.png',image,url=full,requested_url=full,inline_url=inline,content_type='image/png',rendition='linked_full_image',source_revision_status='current_image_response_historical_bytes_unverified',historical_digest_match_verified=False)],'date_warnings':[],'capture_kind':'retained','source_format':'archived_atom_feed','derived_source':True,'original_source':original,'archive_url':'https://web.archive.org/web/20160301000000/http://verniman.blogspot.com/feeds/posts/default','archive_observed_at':'2016-03-01T00:00:00Z','source_entry_selector':entry,'source_feed_entry_ordinal':i,'year_evidence':{'kind':'fixture reviewed year'},'source_provenance':{'kind':'fixture selected Atom entry'},'captured_at':'2026-10-21T00:00:00Z'})
 image_raw=b'<h3 class="post-title">Outlook 11/17</h3><div class="post-body"><img src="https://1.bp.blogspot.com/source/s1600/image-only.png"></div>'
 image_gz=gzip.compress(image_raw,mtime=0);(s/'captures/image-only.html.gz').write_bytes(image_gz)
 posts.append({'url':'https://verniman.blogspot.com/2016/image-only.html','session_date':'2016-11-17','title':'Outlook 11/17','html':rec('captures/image-only.html.gz',image_gz,uncompressed_sha256=hashlib.sha256(image_raw).hexdigest()),'images':[rec('assets/source.png',image,url='https://1.bp.blogspot.com/source/s1600/image-only.png',requested_url='https://1.bp.blogspot.com/source/s1600/image-only.png',inline_url='https://1.bp.blogspot.com/source/s1600/image-only.png',content_type='image/png',rendition='linked_full_image',source_revision_status='current_image_response_historical_bytes_unverified',historical_digest_match_verified=False)],'date_warnings':[],'capture_kind':'retained','source_format':'archived_html','derived_source':False})
 try:b.parse_article(b'<div class="post-body">   </div>','https://verniman.blogspot.com/empty.html')
 except ValueError:pass
 else:raise AssertionError('empty body without images was not rejected')
 manifest={'run_id':'fixture2016source','start_date':'2016-01-01','end_date':'2016-12-31','posts':posts,'archive_notice':'Partial archive recovery; historical image bytes remain unverified.'};(s/'capture-manifest.json').write_text(json.dumps(manifest))
 result=b.build(s);assert result['status']=='passed';a=s/'archive';inv=json.loads((a/'archive-manifest.json').read_text());source_files=list((a/'source-payloads').glob('*.xml.gz'));assert len(source_files)==1 and gzip.decompress(source_files[0].read_bytes())==xml
 for r in inv['posts']:
  article=json.loads(gzip.decompress((a/r['capsule']/'article.json.gz').read_bytes()))
  if article['derived_source']:
   assert article['original_source']['path'].startswith('source-payloads/');assert article['source_entry_selector'] in {'first','second'};assert article['year_evidence']=={'kind':'fixture reviewed year'}
  else:assert article['source_body_kind']=='image_only' and article['full_text']==''
  page=(a/r['session_date'][:4]/r['session_date'][5:7]/r['session_date'][8:] /'index.html').read_text();assert 'historical image bytes unverified' in page
  if article['derived_source']:assert 'Selected feed entry HTML' in page and 'Original archived feed XML' in page
  else:assert 'contains images without body text' in page
 assert 'Partial archive recovery' in (a/'index.html').read_text() and 'Partial archive recovery' in (a/'2016/02/index.html').read_text() and 'Partial archive recovery' in (a/'gap-log.md').read_text()
 metrics=json.loads((a/'metrics.json').read_text());assert metrics['historically_unverified_image_references']==3 and metrics['image_only_source_articles']==1
 b.check(s)
 # The original XML identity is verified independently of derived HTML, before output.
 bad=s/'captures/feed.xml.gz';bad.write_bytes(gz+b'changed')
 try:b.check(s)
 except ValueError:pass
 else:raise AssertionError('changed original source XML was not rejected')
print(json.dumps({'status':'passed','derived_wrappers':2,'deduplicated_original_xml_payloads':1,'original_xml_bytes_preserved':True,'entry_selectors_and_year_evidence_retained':True,'derived_html_and_original_xml_links':True,'uncertain_image_captions':3,'image_only_source_accepted':True,'empty_body_without_images_rejected':True,'archive_notice_present':True,'changed_original_xml_rejected':True}))
