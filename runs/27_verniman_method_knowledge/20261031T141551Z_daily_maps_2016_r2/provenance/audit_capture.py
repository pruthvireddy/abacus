from html.parser import HTMLParser
from urllib.parse import urljoin
import xml.etree.ElementTree as ET

class Bodies(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.div_depth=0;self.body_depth=None;self.current=None;self.rows=[];self.anchors=[]
        self.post_id=None;self.title='';self.title_active=False;self.skip=0
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=='a' and (a.get('name') or '').isdigit():self.post_id=a['name']
        if tag in {'h1','h2','h3'} and 'post-title' in a.get('class','').split():self.title='';self.title_active=True
        if tag=='div':
            self.div_depth+=1
            if 'post-body' in a.get('class','').split():
                assert self.current is None
                self.body_depth=self.div_depth;self.current={'id':self.post_id,'title':self.title.strip(),'parts':[],'images':[],'links':[]};self.anchors=[]
        if self.current is not None:
            if tag in {'script','style','template'}:self.skip+=1
            if tag=='a':
                self.anchors.append(a.get('href'))
                if a.get('href'):self.current['links'].append(a['href'])
            if tag=='img' and not self.skip:
                self.current['images'].append({'inline':a.get('src') or a.get('data-src'),'linked':self.anchors[-1] if self.anchors else None})
    def handle_endtag(self,tag):
        if tag in {'h1','h2','h3'}:self.title_active=False
        if self.current is not None:
            if tag=='a' and self.anchors:self.anchors.pop()
            if tag in {'script','style','template'} and self.skip:self.skip-=1
        if tag=='div':
            if self.body_depth==self.div_depth:
                self.rows.append(self.current);self.current=None;self.body_depth=None
            self.div_depth-=1
    def handle_data(self,data):
        if self.title_active:self.title+=data
        if self.current is not None and not self.skip:self.current['parts'].append(data)

def html_source(raw,post):
    p=Bodies();p.feed(raw.decode('utf-8','replace'))
    matches=[r for r in p.rows if r['id']==str(post['source_post_id'])]
    if not matches and len(p.rows)==1:matches=p.rows
    assert len(matches)==1,(post['url'],len(p.rows),len(matches))
    return matches[0]

def atom_source(raw,post):
    root=ET.fromstring(raw);ns={'a':'http://www.w3.org/2005/Atom'}
    es=root.findall('a:entry',ns)
    matches=[(i,e) for i,e in enumerate(es,1) if e.findtext('a:id',namespaces=ns)==post['source_entry_selector']]
    assert len(matches)==1
    ordinal,e=matches[0];assert ordinal==post['source_feed_entry_ordinal'],(ordinal,post['source_feed_entry_ordinal'])
    title=e.findtext('a:title',default='',namespaces=ns)
    body=e.findtext('a:content',default='',namespaces=ns)
    q=Bodies();q.feed('<h3 class="post-title">'+title+'</h3><div class="post-body">'+body+'</div>');assert len(q.rows)==1
    row=q.rows[0];row.update(id=post['source_post_id'],title=title,ordinal=ordinal,entry_id=e.findtext('a:id',namespaces=ns))
    return row

if __name__=='__main__':
 import argparse,csv,gzip,hashlib,json,re,sys
 from pathlib import Path
 from datetime import date,timedelta
 from collections import Counter
 from urllib.parse import urlsplit,urljoin,unquote
 sys.dont_write_bytecode=True
 root=Path('/Users/pruthvi/Documents/projects/abacus')
 ap=argparse.ArgumentParser();ap.add_argument('--stage',type=Path,default=Path(__file__).resolve().parents[1]);args=ap.parse_args();stage=args.stage.resolve()
 errors=[];checked=set()
 def digest(raw):return hashlib.sha256(raw).hexdigest()
 def raw_record(base,r,label):
  path=(base/r['path']).resolve();path.relative_to(base.resolve());raw=path.read_bytes()
  assert len(raw)==r['bytes'] and digest(raw)==r['sha256'],('bytes',label,str(path))
  checked.add(str(path))
  if r['path'].endswith('.gz'):
   raw=gzip.decompress(raw)
   if r.get('uncompressed_sha256'):assert digest(raw)==r['uncompressed_sha256'],('uncompressed hash',label)
   if r.get('uncompressed_bytes') is not None:assert len(raw)==r['uncompressed_bytes'],('uncompressed length',label)
  return raw
 def textkey(parts):return re.sub(r'\s+','',''.join(parts))
 cm=json.loads((stage/'capture-manifest.json').read_text());archive=stage/'archive';inventory=json.loads((archive/'archive-manifest.json').read_text());metrics=json.loads((archive/'metrics.json').read_text())
 source_path='data/raw/blogspot/verniman/archive_html/20261021T041009Z_2016_review_00a94d4c/collection_manifest.final.json'
 pins=[r for r in cm['retained_inputs'] if r['path']==source_path];assert len(pins)==1
 source=json.loads(raw_record(root,pins[0],'selected archive collection'))
 assert pins[0]['sha256']=='e8d825d0cd0c7a9c8fc97e74d9a91eb5523fb4acb461cf9e92dba0a101b9222f'
 for r in cm.get('retained_source_verifications',[]):raw_record(root,r,'verified original source')
 for key in ['chronology_review','collection_completion_review','archive_capture_manifest','collection_review']:raw_record(root,source[key],key)
 assert cm['start_date']=='2016-01-01' and cm['end_date']=='2016-12-31'
 assert cm['capture_method']=='hash_verified_retained_archival_collection' and cm['lower_boundary_reached'] is False
 assert cm['historical_full_year_completeness_claimed'] is False and cm['observed_archive_coverage_only'] is True
 assert cm['stop_reason']=='retained_archive_observed_coverage_only'
 assert len(cm['posts'])==160 and not cm.get('excluded_context_posts')
 expected={(p['url'],p['session_date']):p for p in source['posts']};assert len(expected)==160
 assert {(p['url'],p['session_date']) for p in cm['posts']}==set(expected)
 assert [(p['session_date'],p['url']) for p in cm['posts']]==sorted([(p['session_date'],p['url']) for p in cm['posts']],reverse=True)
 assert len(inventory['posts'])==160
 counts=Counter();bodyless=[];raw_xml=set();image_hashes=set();seen_dates=set()
 for p,ir in zip(cm['posts'],inventory['posts']):
  old=expected[(p['url'],p['session_date'])];fmt=old['source_format'];counts[fmt]+=1
  assert p['capture_kind']=='retained' and p['title']==old['title'] and p['source_format']==fmt
  assert p['archive_url']==old['archive_url'] and p['archive_observed_at']==old['archive_observed_at']
  assert p['captured_at']==old['captured_at'] and p['date_method']==old['session_date_method']
  expected_year={key:value for key,value in old['year_evidence'].items() if key!='source_context_excerpt'}
  if 'source_context_excerpt' in old['year_evidence']:
   excerpt=old['year_evidence']['source_context_excerpt'].encode()
   expected_year['source_context_excerpt_identity']={'sha256':digest(excerpt),'utf8_bytes':len(excerpt),'retained_in_source_manifest':pins[0],'source_post_id':old.get('source_post_id')}
  assert p['year_evidence']==expected_year and 'source_context_excerpt' not in p['year_evidence']
  d=date.fromisoformat(p['session_date']);seen_dates.add(d.isoformat());pairs=re.findall(r'\bOutlook\s+(\d{1,2})/(\d{1,2})\b',old['title'],re.I);assert len(pairs)==1 and tuple(map(int,pairs[0]))==(d.month,d.day) and d.year==2016
  if fmt=='archived_atom_feed':
   original=raw_record(root,old['atom'],'original Atom XML');article=atom_source(original,old)
   assert p['derived_source'] is True and p['source_entry_selector']==old['source_entry_selector'] and p['source_feed_entry_ordinal']==old['source_feed_entry_ordinal']
   assert raw_record(stage,p['original_source'],'stage original XML')==original
   raw_xml.add(digest(original))
   source_clock=old['atom'].get('captured_at') or old['captured_at']
  else:
   original=raw_record(root,old['html'],'original archived HTML');article=html_source(original,old)
   assert p['derived_source'] is False and not p.get('original_source')
   source_clock=old['html'].get('captured_at') or old['captured_at']
  assert p['source_capture_at']==source_clock
  staged=raw_record(stage,p['html'],'stage HTML')
  if fmt!='archived_atom_feed':assert staged==original
  selected=html_source(staged,{'source_post_id':old['source_post_id'],'url':p['url']})
  assert selected['title']==article['title']==old['title'] and textkey(selected['parts'])==textkey(article['parts'])
  if not textkey(article['parts']):bodyless.append({'session_date':p['session_date'],'url':p['url'],'title':p['title'],'image_elements':len(article['images'])})
  assert len(p['images'])==len(article['images'])==len(old['images'])
  for im,element,oldim in zip(p['images'],article['images'],old['images']):
   inline=urljoin(p['url'],element['inline']);linked=urljoin(p['url'],element['linked']) if element['linked'] else inline
   preferred=linked if re.search(r'(?:blogger\.googleusercontent\.com|bp\.blogspot\.com)/',linked) else inline
   assert im['inline_url']==inline and im['requested_url']==preferred and im['url']==preferred==oldim['url']
   assert im['capture_kind']=='retained' and im['captured_at']==oldim['captured_at']
   assert im['source_revision_status']=='current_image_response_historical_bytes_unverified' and im['historical_digest_match_verified'] is False
   assert im['original_image_record']==oldim
   assert raw_record(stage,im,'stage image')==raw_record(root,oldim,'original image fallback')
   image_hashes.add(im['sha256']);counts['images']+=1
  capsule=archive/ir['capsule'];assert gzip.decompress((capsule/'source.html.gz').read_bytes())==staged
  saved=json.loads(gzip.decompress((capsule/'article.json.gz').read_bytes()))
  saved_body=Bodies();saved_body.feed(staged.decode());assert len(saved_body.rows)==1
  assert textkey(saved['full_text'])==textkey(article['parts'])
  for key in ['source_format','archive_url','archive_observed_at','source_entry_selector','source_feed_entry_ordinal','derived_source','year_evidence','source_provenance','image_revision_qualification']:assert saved.get(key)==p.get(key),(key,p['url'])
  assert len(saved['images'])==len(p['images'])
  for sim,pim in zip(saved['images'],p['images']):
   assert raw_record(archive,sim,'reader image')==raw_record(stage,pim,'stage image')
   assert sim['source_revision_status']=='current_image_response_historical_bytes_unverified' and sim['historical_digest_match_verified'] is False
  page=archive/p['session_date'][:4]/p['session_date'][5:7]/p['session_date'][8:] /'index.html';page_text=page.read_text()
  assert page_text.count('Current source-image fallback; historical image bytes unverified.')==len(p['images'])
  if not textkey(article['parts']):assert saved['source_body_kind']=='image_only' and 'contains images without body text' in page_text
  else:assert saved['source_body_kind']=='text_and_media'
  assert 'Retained historical archive' in page_text and 'Archived source' in page_text
  parser=Bodies();parser.feed(page_text)
  # Images in the rendered source-text are checked independently of source wrappers.
  rendered=[]
  class Rendered(HTMLParser):
   def handle_starttag(self,t,attrs):
    if t=='img':rendered.append(dict(attrs).get('src'))
  rp=Rendered();rp.feed(page_text)
  assert len(rendered)==len(saved['images'])
  for value,sim in zip(rendered,saved['images']):assert (page.parent/unquote(value)).resolve()==(archive/sim['path']).resolve()
  if fmt=='archived_atom_feed':
   assert raw_record(archive,saved['original_source'],'reader original XML')==original
   assert 'Selected feed entry HTML' in page_text and 'Original archived feed XML' in page_text
   assert not (saved['original_source']['path'].startswith('../'))
  counts['text_articles']+=1
 assert counts['archived_html']==134 and counts['archived_page_post']==1 and counts['archived_atom_feed']==25
 assert counts['images']==560 and len(image_hashes)==560 and len(raw_xml)==1
 original_payloads=list((archive/'source-payloads').glob('*.xml.gz'));assert len(original_payloads)==1 and digest(gzip.decompress(original_payloads[0].read_bytes())) in raw_xml
 assert len(bodyless)==3 and {x['session_date'] for x in bodyless}=={'2016-11-17','2016-11-23','2016-12-01'}
 rows=list(csv.DictReader((archive/'coverage.csv').open()));dates=[];d=date(2016,12,31)
 while d>=date(2016,1,1):dates.append(d.isoformat());d-=timedelta(days=1)
 assert [r['date'] for r in rows]==dates and len(rows)==366
 for r in rows:assert int(r['post_count'])==(1 if r['date'] in seen_dates else 0)
 weekday=sum(r['post_count']=='0' and date.fromisoformat(r['date']).weekday()<5 for r in rows);weekend=sum(r['post_count']=='0' and date.fromisoformat(r['date']).weekday()>=5 for r in rows)
 assert weekday==101 and weekend==105 and '2016-02-29' in seen_dates
 assert metrics['calendar_days']==366 and metrics['map_records']==160 and metrics['days_with_maps']==160 and metrics['retained_image_references']==560 and metrics['unique_image_files']==560 and metrics['historically_unverified_image_references']==560
 assert metrics['image_only_source_articles']==3
 assert metrics['retained_map_records']==160 and metrics['live_map_records']==0 and metrics['duplicate_date_count']==0 and metrics['unassigned_or_boundary_records']==0
 for entry in inventory['indexes']:
  if entry['path']=='2016/02/index.html':assert len(entry['dates'])==29
 assert cm['archive_notice'] in (archive/'gap-log.md').read_text()
 assert 'Coverage has gaps' in (archive/'index.html').read_text()

 current=json.loads(raw_record(stage,cm['current_source_observations'],'current observations descriptor'))
 assert len(current['records'])==8
 assert cm['attempts']==current['records'] and cm['sitemaps']==[r for r in current['records'] if r['observation_kind']=='current_sitemap']
 locators=[];observed_rewrites={};observed_status=Counter()
 for record in current['records']:
  observed=raw_record(stage,record,'current raw observation');observed_status[(record['observation_kind'],record['http_status'])]+=1
  if record['observation_kind']=='current_sitemap':
   tree=ET.fromstring(observed)
   if tree.tag.endswith('urlset'):
    locators += [e.findtext('{http://www.sitemaps.org/schemas/sitemap/0.9}loc') for e in tree]
  elif record['observation_kind']=='current_educational_rewrite':
   parsed=Bodies();parsed.feed(observed.decode('utf-8'));assert len(parsed.rows)==1
   row=parsed.rows[0];assert not re.findall(r'\bOutlook\s+(\d{1,2})/(\d{1,2})\b',row['title']+' '+''.join(row['parts']),re.I)
   observed_rewrites[record['url']]=row['title']
 assert len(locators)==current['sitemap_locator_count']==2210
 assert sorted(set(locators)&{p['url'] for p in source['posts']})==sorted(current['selected_archived_urls_in_current_sitemap'])
 assert observed_rewrites=={'https://verniman.blogspot.com/2016/05/outlook-0518.html':'The VWAP Setups','https://verniman.blogspot.com/2016/05/outlook-0519.html':'The Scalp Setups'}
 assert observed_status[('current_sitemap',200)]==4 and observed_status[('current_live_probe',404)]==2 and observed_status[('current_educational_rewrite',200)]==2
 for rewrite in current['current_rewrites']:assert observed_rewrites[rewrite['url']]==rewrite['current_title'] and rewrite['current_outlook_month_day'] is None
 print(json.dumps({'audit':'independent_2016_archive_source_retention','passed':True,'checked_unique_files':len(checked),'posts':160,'distinct_dated_days':160,'source_formats':{k:counts[k] for k in ['archived_html','archived_page_post','archived_atom_feed']},'full_texts_checked':counts['text_articles'],'ordered_image_elements':560,'unique_image_payloads':560,'historically_unverified_image_references':560,'original_xml_payloads':len(original_payloads),'exact_atom_selectors_checked':25,'image_only_source_bodies':bodyless,'calendar_days':366,'date_order':'descending','february_days':29,'leap_day_map':True,'weekday_gaps':101,'weekend_gaps':105,'duplicates':0,'lower_boundary_observed':False,'historical_full_year_completeness_claimed':False,'current_raw_observations_verified':8,'current_sitemap_locators':2210,'current_404_probes':2,'current_educational_rewrites_verified':observed_rewrites,'sanitized_year_evidence_verified':True,'errors':[]},indent=2))
