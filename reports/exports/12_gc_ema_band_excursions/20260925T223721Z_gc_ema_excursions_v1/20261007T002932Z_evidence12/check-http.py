# Read only the generated local static preview; no external source requests.
import csv,hashlib,html,io,json,urllib.request,urllib.error
from pathlib import Path
ROOT=Path(__file__).resolve().parents[5];OUT=Path(__file__).resolve().parent
p=json.loads((OUT/'publication.json').read_text());base='http://127.0.0.1:4174';checks=[]
def get(path):
 with urllib.request.urlopen(base+path) as r:return r.status,dict(r.headers),r.read()
status,headers,body=get('/reports/'+p['id']+'/');assert status==200
page=body.decode();assert html.escape(p['title']) in page
for d in p.get('downloads',[]):
 status,h,b=get('/publications/'+p['id']+'/'+d['path']);assert status==200
 assert hashlib.sha256(b).hexdigest()==d['sha256']
 assert h['Content-Type']=='text/csv; charset=utf-8' and h['X-Content-Type-Options']=='nosniff'
 assert d['path'].split('/')[-1] in h['Content-Disposition'] and h['Content-Disposition'].startswith('attachment;')
 rows=list(csv.reader(io.StringIO(b.decode())));assert rows[0]==d['columns'] and len(rows)-1==d['rowCount']
 checks.append({'path':d['path'],'bytes':len(b),'sha256':d['sha256'],'headers':h,'saved_rows':d['rowCount']})
for s in p['sections']:
 assert 'id="section-'+s['id']+'"' in page
 if s['kind']=='figure':
  status,h,b=get('/publications/'+p['id']+'/'+s['path']);assert status==200 and b==(OUT/s['path']).read_bytes()
for ref in p.get('references',[]):
 assert 'id="reference-'+ref['id']+'"' in page
 if ref['kind']=='external':assert 'href="'+html.escape(ref['url'],quote=True)+'"' in page
catalog=json.loads((ROOT/'apps/narada/content/studies.json').read_text());study=next(s for s in catalog['studies'] if s['featuredPublicationId']==p['id']);status,h,b=get('/studies/'+study['slug']+'/');assert status==200
for rid in [p['id']]+[r['publicationId'] for r in study.get('relatedPublications',[])]:
 assert 'href="/reports/'+rid+'/"' in b.decode();assert get('/reports/'+rid+'/')[0]==200
try:get('/reports/phase4-missing-page/')
except urllib.error.HTTPError as e: assert e.code==404
else:raise AssertionError('Missing page did not return 404')
record={'publication_id':p['id'],'passed':True,'route_status':200,'study_slug':study['slug'],'downloads':checks,'figures':sum(s['kind']=='figure' for s in p['sections']),'references':len(p.get('references',[])),'missing_page_status':404,'limitations':'Local static headers and bytes verified; hosted-provider headers require Phase 5 verification.'}
(OUT/'static-verification.json').write_text(json.dumps(record,indent=2)+'\n');print(p['id']+' HTTP/asset/hash/header/navigation checks passed')
