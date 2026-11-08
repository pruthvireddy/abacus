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
 from collections import Counter
 from datetime import date,timedelta
 from pathlib import Path
 sys.dont_write_bytecode=True
 root=Path('/Users/pruthvi/Documents/projects/abacus')
 ap=argparse.ArgumentParser();ap.add_argument('--stage',type=Path,default=root/'work/27_verniman_method_knowledge/20261031T155759Z_daily_maps_2011');ap.add_argument('--source-manifest',type=Path);ap.add_argument('--expected-source-sha256');args=ap.parse_args();stage=args.stage.resolve()
 checked=set()
 def digest(raw):return hashlib.sha256(raw).hexdigest()
 def raw_record(base,record,label):
  path=(base/record['path']).resolve();path.relative_to(base.resolve());raw=path.read_bytes()
  assert len(raw)==record['bytes'] and digest(raw)==record['sha256'],(label,path);checked.add(str(path))
  if path.suffix=='.gz':
   raw=gzip.decompress(raw)
   if record.get('uncompressed_sha256'):assert digest(raw)==record['uncompressed_sha256']
   if record.get('uncompressed_bytes') is not None:assert len(raw)==record['uncompressed_bytes']
  return raw
 cm=json.loads((stage/'capture-manifest.json').read_text());archive=stage/'archive';inventory=json.loads((archive/'archive-manifest.json').read_text());metrics=json.loads((archive/'metrics.json').read_text())
 assert cm['start_date']=='2011-01-01' and cm['end_date']=='2011-12-31'
 if args.source_manifest:
  source_path=args.source_manifest.resolve().relative_to(root).as_posix();pins=[r for r in cm['retained_inputs'] if r['path']==source_path]
 else:pins=[r for r in cm['retained_inputs'] if r['path'].endswith('.json')]
 assert len(pins)==1
 source_raw=raw_record(root,pins[0],'explicit selected collection pin');source=json.loads(source_raw)
 if args.expected_source_sha256:assert digest(source_raw)==args.expected_source_sha256
 assert source['posts']==cm['posts']==inventory['posts']==[]
 for rec in cm.get('retained_source_verifications',[]):raw_record(root,rec,'verified original source')
 for key in ['chronology_review','collection_completion_review','archive_capture_manifest','collection_review']:
  if source.get(key):raw_record(root,source[key],key)
 assert cm['capture_method']=='hash_verified_retained_archival_collection' and cm['seed_url'] is None
 assert cm['lower_boundary_reached'] is False and cm['historical_full_year_completeness_claimed'] is False and cm['observed_archive_coverage_only'] is True
 review=cm['empty_daily_selection_review']
 assert review['status']=='reviewed_no_in_scope_daily_plans' and review['requested_start_date']=='2011-01-01' and review['anchor_session_date']=='2011-12-31' and review['reason']
 assert {k:v for k,v in review.items() if k!='retained_review'}==source['empty_daily_selection_review']
 authored=json.loads(raw_record(root,review['review_record'],'authored empty daily-source review'))
 assert authored['empty_daily_selection_review']=={k:v for k,v in source['empty_daily_selection_review'].items() if k!='review_record'}
 precheck=json.loads(raw_record(root,review['independent_selection_precheck'],'independent exact source selection review'))
 assert precheck['status']=='passed' and precheck['selected_source_ids']==[]
 assert all(type(precheck[k]) is int and precheck[k]==0 for k in ['selected_records','dated','undated','image_references','unique_image_hashes'])
 assert precheck['raw_source_revisions']==70 and precheck['actual_post_body_instances']==73 and precheck['successfully_captured_sources']==70 and precheck['failed_indexed_locators']==0
 assert precheck['raw_source_formats']=={'archived_html':17,'archived_atom_feed':50,'current_html':3}
 assert precheck['excluded_archived_context_records']==67 and precheck['excluded_current_context_records']==3
 assert precheck['raw_image_references']==131 and precheck['retained_raw_image_references']==81 and precheck['unique_retained_raw_images']==58
 assert precheck['successful_raw_image_pairs']==59 and precheck['raw_missing_images']==50 and precheck['missing_tracking_pixel_references']==50 and precheck['unique_missing_image_urls']==38
 assert precheck['missing_authored_chart_references']==0 and precheck['raw_inline_fallbacks']==0
 assert len(precheck['exact_later_year_full_body_matches'])==3
 assert sorted(m['exact_frozen_later_year_matches'][0]['session_date'] for m in precheck['exact_later_year_full_body_matches'])==['2022-05-25','2022-05-27','2022-06-08']
 assert len(precheck['frozen_later_year_inventories'])==15 and precheck['atom_entry_records']==50 and precheck['atom_unique_ids']==38 and precheck['atom_repeated_ids']==12
 raw_recovery_record=source['archive_capture_manifest'];assert raw_recovery_record==precheck['recovery_manifest'] or all(raw_recovery_record[k]==precheck['recovery_manifest'][k] for k in ['path','bytes','sha256'])
 assert raw_recovery_record['sha256']=='24cd449faeee26a091b9e06de07a6c40ef47714a2c40dc183d7d58e3e0696c82'
 raw_recovery=json.loads(raw_record(root,raw_recovery_record,'complete raw recovery'))
 assert len(raw_recovery['posts'])==70 and len(raw_recovery['files'])==311
 assert not any(p.get('capture_failed') for p in raw_recovery['posts'])
 for rec in raw_recovery['files']:raw_record(root,rec,'raw recovery inventoried bytes')
 retained=raw_record(stage,review['retained_review'],'retained reader source review');assert retained==(archive/'source-review.json').read_bytes()
 assert not list((archive/'assets').glob('*')) and not (archive/'source-payloads').exists()
 assert 'No in-scope daily plans could be established' in cm['archive_notice']
 assert 'No in-scope daily plans could be established' in (archive/'index.html').read_text() and 'source-review.json' in (archive/'index.html').read_text()
 for suffix in ['*.png','*.jpg','*.jpeg','*.gif','*.webp']:assert not list(archive.rglob(suffix))
 rows=list(csv.DictReader((archive/'coverage.csv').open()));dates=[r['date'] for r in rows]
 expected=[(date(2011,12,31)-timedelta(days=i)).isoformat() for i in range(365)]
 assert dates==expected and len(set(dates))==365 and not any(d.endswith('-02-29') for d in dates)
 for row in rows:
  day=date.fromisoformat(row['date']);assert row['weekday']==day.strftime('%A')
  assert all(row[k]=='0' for k in ['post_count','live_post_count','retained_post_count','image_count','missing_image_count'])
  assert row['status']==('no_dated_post_observed_weekend' if day.weekday()>=5 else 'no_dated_post_observed_weekday')
  assert 'does not prove no post existed' in row['notes']
  folder=archive/day.strftime('%Y/%m/%d');assert (folder/'index.html').is_file() and (folder/'README.md').is_file()
 assert not (archive/'2011/02/29').exists() and not (archive/'2010').exists() and not (archive/'2012').exists()
 indexes={r['path']:r['dates'] for r in inventory['indexes']}
 assert indexes['index.html']==dates and indexes['2011/index.html']==dates and len(indexes['2011/02/index.html'])==28
 for m in range(1,13):assert indexes[f'2011/{m:02}/index.html']==[d for d in dates if int(d[5:7])==m]
 assert metrics['calendar_days']==365 and metrics['map_records']==0 and metrics['days_with_maps']==0
 assert metrics['weekday_gaps']==260 and metrics['weekend_gaps']==105
 for k in ['image_references','unique_image_files','retained_image_references','live_map_records','retained_map_records','unassigned_or_boundary_records']:assert metrics[k]==0
 files={r['path'] for r in inventory['files']};actual={p.relative_to(archive).as_posix() for p in archive.rglob('*') if p.is_file()}-{'archive-manifest.json'};assert files==actual and len(files)==len(inventory['files'])
 for rec in inventory['files']:raw_record(archive,rec,'reader inventory')
 print(json.dumps({'status':'passed','scope':'Independent pinned source-selection, raw outcomes and complete descending 2011 reader/calendar audit; observed coverage does not prove historical absence.','checked_unique_files':len(checked),'selected_records':0,'dated':0,'undated':0,'image_references':0,'unique_image_hashes':0,'calendar_days':365,'february_days':28,'leap_day_present':False,'weekday_gaps':260,'weekend_gaps':105,'raw_source_revisions':70,'actual_body_instances':73,'archived_context_records':67,'current_only_context_records':3,'exact_frozen_2022_body_matches':3,'raw_image_references':131,'retained_raw_image_references':81,'unique_retained_raw_images':58,'missing_tracking_pixel_references':50,'missing_authored_chart_references':0,'seed_url_is_null':True,'empty_source_review_retained':True,'historical_full_year_completeness_claimed':False},indent=2))

