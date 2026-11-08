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
 from datetime import date,datetime,timedelta
 from collections import Counter,defaultdict
 from urllib.parse import urlsplit,urljoin,unquote
 sys.dont_write_bytecode=True
 root=Path('/Users/pruthvi/Documents/projects/abacus')
 ap=argparse.ArgumentParser();ap.add_argument('--stage',type=Path,default=root/'work/27_verniman_method_knowledge/20261031T143306Z_daily_maps_2015');ap.add_argument('--source-manifest',type=Path);ap.add_argument('--expected-source-sha256');args=ap.parse_args();stage=args.stage.resolve()
 checked=set()
 def digest(raw):return hashlib.sha256(raw).hexdigest()
 def raw_record(base,r,label):
  path=(base/r['path']).resolve();path.relative_to(base.resolve());raw=path.read_bytes()
  assert len(raw)==r['bytes'] and digest(raw)==r['sha256'],('bytes',label,str(path));checked.add(str(path))
  if r['path'].endswith('.gz'):
   raw=gzip.decompress(raw)
   if r.get('uncompressed_sha256'):assert digest(raw)==r['uncompressed_sha256'],('gzip hash',label)
   if r.get('uncompressed_bytes') is not None:assert len(raw)==r['uncompressed_bytes'],('gzip length',label)
  return raw
 def textkey(parts):return re.sub(r'\s+','',''.join(parts))
 def title_pairs(title,order='month_day'):
  pairs={(int(m),int(d)) for m,d in re.findall(r'\b(?:Outlook|Opening(?:\s+Print)?)\s+(\d{1,2})/(\d{1,2})\b',title,re.I)}
  compact={(int(m),int(d)) for m,d in re.findall(r'\bOpening(?:\s+Print)?\s+(\d{2})(\d{2})\b',title,re.I)}
  if order=='day_month':
   assert not compact and len(pairs)==1
   first,second=next(iter(pairs));assert first>12 and 1<=second<=12
   pairs={(second,first)}
  else:assert order=='month_day';pairs.update(compact)
  for m,d in pairs:date(2015,m,d)
  return pairs
 def source_key(p):
  sr=p.get('atom') if p['source_format']=='archived_atom_feed' else p.get('html')
  return p['url'],p.get('session_date'),p['source_format'],p.get('archive_url'),sr['sha256']
 def capture_key(p):
  sr=p['source_provenance']['original_source_record']
  return p['url'],p.get('session_date'),p['source_format'],p.get('archive_url'),sr['sha256']
 cm=json.loads((stage/'capture-manifest.json').read_text());archive=stage/'archive';inventory=json.loads((archive/'archive-manifest.json').read_text());metrics=json.loads((archive/'metrics.json').read_text())
 assert cm['start_date']=='2015-01-01' and cm['end_date']=='2015-12-31'
 if args.source_manifest:
  source_path=args.source_manifest.resolve().relative_to(root).as_posix()
  pins=[r for r in cm['retained_inputs'] if r['path']==source_path]
 else:
  pins=[r for r in cm['retained_inputs'] if r['path'].endswith('.json')]
 assert len(pins)==1,('selected collection pin',pins)
 source_raw=raw_record(root,pins[0],'selected source collection');source=json.loads(source_raw)
 if args.expected_source_sha256:assert digest(source_raw)==args.expected_source_sha256
 for r in cm.get('retained_source_verifications',[]):raw_record(root,r,'verified original source')
 for key in ['chronology_review','collection_completion_review','archive_capture_manifest','collection_review']:
  if source.get(key):raw_record(root,source[key],key)
 assert cm['capture_method']=='hash_verified_retained_archival_collection' and cm['lower_boundary_reached'] is False
 assert cm['historical_full_year_completeness_claimed'] is False and cm['observed_archive_coverage_only'] is True
 expected=defaultdict(list)
 for old in source['posts']:expected[source_key(old)].append(old)
 assert Counter(capture_key(p) for p in cm['posts'])==Counter(source_key(p) for p in source['posts'])
 assert len(inventory['posts'])==len(cm['posts'])
 assert [(p.get('session_date') or '',p['url']) for p in cm['posts']]==sorted([(p.get('session_date') or '',p['url']) for p in cm['posts']],reverse=True)
 counts=Counter();bodyless=[];raw_xml=set();image_hashes=set();date_counts=Counter();undated=[];page_images=defaultdict(list);page_missing=Counter();page_inline=Counter();page_texts={};day_month=[]
 for p,ir in zip(cm['posts'],inventory['posts']):
  old=expected[capture_key(p)].pop(0);fmt=old['source_format'];counts[fmt]+=1
  assert p['capture_kind']=='retained' and p['title']==old['title'] and p['source_format']==fmt
  assert p.get('archive_url')==old.get('archive_url') and p.get('archive_observed_at')==old.get('archive_observed_at')
  assert p.get('captured_at')==old.get('captured_at') and p['date_method']==old['session_date_method']
  assert old.get('reviewed_daily_plan') is True and p.get('reviewed_daily_plan') is True
  assert re.match(r'^\s*(?:Outlook|Opening)\b',old['title'],re.I),('unsupported selected daily title',old['title'])
  review=old['date_review'];assert p['date_review']==review and review['source_title']==old['title']
  expected_year={k:v for k,v in old['year_evidence'].items() if k!='source_context_excerpt'}
  if 'source_context_excerpt' in old['year_evidence']:
   excerpt=old['year_evidence']['source_context_excerpt'].encode();expected_year['source_context_excerpt_identity']={'sha256':digest(excerpt),'utf8_bytes':len(excerpt),'retained_in_source_manifest':pins[0],'source_post_id':old.get('source_post_id')}
  assert p['year_evidence']==expected_year and 'source_context_excerpt' not in p['year_evidence'] and p['year_evidence']['year']==2015
  if fmt=='archived_atom_feed':
   original=raw_record(root,old['atom'],'original Atom XML');article=atom_source(original,old)
   assert p['derived_source'] is True and p['source_entry_selector']==old['source_entry_selector'] and p['source_feed_entry_ordinal']==old['source_feed_entry_ordinal']
   assert raw_record(stage,p['original_source'],'stage original XML')==original;raw_xml.add(digest(original));source_clock=old['atom'].get('captured_at') or old.get('captured_at')
  else:
   original=raw_record(root,old['html'],'original archived HTML');article=html_source(original,old)
   assert p['derived_source'] is False and not p.get('original_source');source_clock=old['html'].get('captured_at') or old.get('captured_at')
  assert p['source_capture_at']==source_clock
  assert ' '.join(article['title'].split())==old['title']
  stamp=p.get('session_date');order=review.get('date_order','month_day');pairs=title_pairs(old['title'],order)
  if stamp is None:
   assert not pairs and review['status']=='undated_title_missing_month_day' and old.get('date_warnings')
   assert not title_pairs(' '.join(article['parts'])),('undated explicit body date',p['url']);undated.append({'url':p['url'],'title':p['title']})
  else:
   d=date.fromisoformat(stamp);assert d.year==2015 and pairs=={(d.month,d.day)} and review['status']=='dated_title';date_counts[stamp]+=1
   if order=='day_month':
    assert fmt=='archived_atom_feed' and review.get('reason')
    tree=ET.fromstring(original);ns={'a':'http://www.w3.org/2005/Atom'};entry=next(e for e in tree.findall('a:entry',ns) if e.findtext('a:id',namespaces=ns)==old['source_entry_selector'])
    published=entry.findtext('a:published',namespaces=ns);assert review['corroborating_published_at']==published and datetime.fromisoformat(published).date().isoformat()==stamp
    day_month.append({'url':p['url'],'title':p['title'],'session_date':stamp,'entry_id':old['source_entry_selector'],'published':published})
  staged=raw_record(stage,p['html'],'stage selected HTML')
  if fmt!='archived_atom_feed':assert staged==original
  selected=html_source(staged,{'source_post_id':old['source_post_id'],'url':p['url']});assert ' '.join(selected['title'].split())==old['title'] and textkey(selected['parts'])==textkey(article['parts'])
  if not textkey(article['parts']):bodyless.append({'session_date':stamp,'url':p['url'],'title':p['title'],'images':len(article['images'])})
  assert len(p['images'])==len(article['images'])==len(old['images'])
  capsule=archive/ir['capsule'];assert gzip.decompress((capsule/'source.html.gz').read_bytes())==staged
  saved=json.loads(gzip.decompress((capsule/'article.json.gz').read_bytes()));assert textkey(saved['full_text'])==textkey(article['parts'])
  for key in ['source_format','archive_url','archive_observed_at','source_entry_selector','source_feed_entry_ordinal','derived_source','year_evidence','source_provenance','reviewed_daily_plan','date_review']:assert saved.get(key)==p.get(key),(key,p['url'])
  assert len(saved['images'])==len(p['images'])
  page=archive/stamp[:4]/stamp[5:7]/stamp[8:]/'index.html' if stamp else archive/'undated/index.html'
  page_texts[page]=page.read_text()
  for im,sim,element,oldim in zip(p['images'],saved['images'],article['images'],old['images']):
   inline=urljoin(p['url'],element['inline']);linked=urljoin(p['url'],element['linked']) if element['linked'] else inline
   preferred=linked if re.search(r'(?:blogger\.googleusercontent\.com|bp\.blogspot\.com)/',linked) else inline
   assert im['inline_url']==inline and im['requested_url']==preferred and oldim['original_image_url']==preferred
   assert im['original_image_record']==oldim
   counts['image_elements']+=1
   if oldim['kind']=='missing_source_image':
    assert not im.get('path') and not sim.get('path') and im['error']==oldim['error'] and oldim['error'];counts['missing_images']+=1;page_missing[page]+=1
    continue
   expected_url=inline if oldim.get('rendition')=='inline_thumbnail' else preferred
   assert im['url']==oldim['url']==expected_url
   assert im['capture_kind']=='retained' and im['captured_at']==oldim['captured_at']
   assert im['source_revision_status']=='current_image_response_historical_bytes_unverified' and im['historical_digest_match_verified'] is False
   assert raw_record(stage,im,'stage image')==raw_record(root,oldim,'original fallback image')==raw_record(archive,sim,'reader image')
   assert sim['source_revision_status']==im['source_revision_status'] and sim['historical_digest_match_verified'] is False
   if oldim.get('rendition')=='inline_thumbnail':assert im['full_size_error']==oldim['full_size_error'] and im['full_size_error'];counts['inline_images']+=1;page_inline[page]+=1
   image_hashes.add(im['sha256']);counts['retained_images']+=1;page_images[page].append(sim)
  if fmt=='archived_atom_feed':assert raw_record(archive,saved['original_source'],'reader original XML')==original and 'Original archived feed XML' in page_texts[page]
  assert saved['source_body_kind']==('text_and_media' if textkey(article['parts']) else 'image_only')
  counts['full_texts']+=1
 for page,text in page_texts.items():
  rendered=[]
  class Rendered(HTMLParser):
   def handle_starttag(self,t,attrs):
    if t=='img':rendered.append(dict(attrs).get('src'))
  parser=Rendered();parser.feed(text)
  assert len(rendered)==len(page_images[page]),('rendered images',str(page),len(rendered),len(page_images[page]))
  for value,sim in zip(rendered,page_images[page]):assert (page.parent/unquote(value)).resolve()==(archive/sim['path']).resolve()
  assert text.count('Current source-image fallback; historical image bytes unverified.')==len(page_images[page])
  assert text.count('Image unavailable.')==page_missing[page]
  assert text.count('Inline rendition retained; full-size source unavailable.')==page_inline[page]
  assert 'Retained historical archive' in text
 original_payloads=list((archive/'source-payloads').glob('*.xml.gz')) if (archive/'source-payloads').exists() else []
 assert len(original_payloads)==len(raw_xml)
 for x in original_payloads:assert digest(gzip.decompress(x.read_bytes())) in raw_xml
 rows=list(csv.DictReader((archive/'coverage.csv').open()));days=[];d=date(2015,12,31)
 while d>=date(2015,1,1):days.append(d.isoformat());d-=timedelta(days=1)
 assert [r['date'] for r in rows]==days and len(rows)==365
 for row in rows:assert int(row['post_count'])==date_counts[row['date']]
 weekday=sum(not int(r['post_count']) and date.fromisoformat(r['date']).weekday()<5 for r in rows);weekend=sum(not int(r['post_count']) and date.fromisoformat(r['date']).weekday()>=5 for r in rows)
 assert metrics['calendar_days']==365 and metrics['map_records']==sum(date_counts.values()) and metrics['days_with_maps']==len(date_counts)
 assert metrics['image_references']==counts['image_elements'] and metrics['retained_image_references']==counts['retained_images'] and metrics['missing_image_references']==counts['missing_images'] and metrics['inline_rendition_references']==counts['inline_images']
 assert metrics['unique_image_files']==len(image_hashes) and metrics['historically_unverified_image_references']==counts['retained_images']
 assert metrics['retained_map_records']==sum(date_counts.values()) and metrics['live_map_records']==0 and metrics['unassigned_or_boundary_records']==len(undated)
 assert metrics['weekday_gaps']==weekday and metrics['weekend_gaps']==weekend and metrics['duplicate_date_count']==sum(n>1 for n in date_counts.values())
 assert metrics['image_only_source_articles']==len(bodyless)
 assert all(len(x['dates'])==28 for x in inventory['indexes'] if x['path']=='2015/02/index.html')
 assert not (archive/'2015/02/29').exists()
 for attempt in cm.get('attempts',[]):
  if attempt.get('path'):raw_record(stage,attempt,'current raw observation')
 for key in ['current_source_observations']:
  if cm.get(key):
   observation=json.loads(raw_record(stage,cm[key],key))
   for r in observation.get('records',[]):raw_record(stage,r,'nested current observation')
 print(json.dumps({'audit':'independent_2015_source_retention','passed':True,'checked_unique_files':len(checked),'selected_daily_sources':len(cm['posts']),'distinct_dated_days':len(date_counts),'dated_maps':sum(date_counts.values()),'undated_daily_plans':len(undated),'source_formats':{k:counts[k] for k in ['archived_html','archived_page_post','archived_atom_feed']},'full_texts_checked':counts['full_texts'],'ordered_image_elements':counts['image_elements'],'retained_image_references':counts['retained_images'],'unique_image_payloads':len(image_hashes),'missing_image_references':counts['missing_images'],'inline_rendition_references':counts['inline_images'],'historically_unverified_image_references':counts['retained_images'],'original_xml_payloads':len(original_payloads),'image_only_bodies':bodyless,'calendar_days':365,'date_order':'descending','february_days':28,'weekday_gaps':weekday,'weekend_gaps':weekend,'duplicate_date_count':sum(n>1 for n in date_counts.values()),'explicit_day_month_reviews':day_month,'lower_boundary_observed':False,'historical_full_year_completeness_claimed':False,'errors':[]},indent=2))
