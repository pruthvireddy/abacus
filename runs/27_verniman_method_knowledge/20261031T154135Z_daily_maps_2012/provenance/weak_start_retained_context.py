import gzip,hashlib,json,re
from pathlib import Path
ROOT=Path('/Users/pruthvi/Documents/projects/abacus')
STAGE=ROOT/'work/27_verniman_method_knowledge/20261031T044414Z_daily_maps_2022'
REC=ROOT/'work/27_verniman_method_knowledge/20261031T154135Z_daily_maps_2012_recovery'
def ident(path):
 raw=path.read_bytes();return {'path':str(path.relative_to(ROOT)),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
cm=json.loads((STAGE/'capture-manifest.json').read_text())
assert (STAGE/'capture-manifest.json').read_bytes()==(ROOT/'runs/27_verniman_method_knowledge/20261031T044414Z_daily_maps_2022/capture-manifest.json').read_bytes()
posts=[p for p in cm['posts'] if p['url']=='https://verniman.blogspot.com/2012/09/weak-start.html'];assert len(posts)==1;p=posts[0]
inventory=json.loads((STAGE/'archive/archive-manifest.json').read_text());q=next(q for q in inventory['posts'] if q['url']==p['url'])
meta=STAGE/'archive'/q['capsule']/'article.json.gz';article=json.loads(gzip.decompress(meta.read_bytes()))
html=STAGE/p['html']['path'];packed=html.read_bytes();raw=gzip.decompress(packed)
assert len(packed)==p['html']['bytes'] and hashlib.sha256(packed).hexdigest()==p['html']['sha256']
assert hashlib.sha256(raw).hexdigest()==p['html']['uncompressed_sha256'] and len(raw)==p['html']['uncompressed_bytes']
assert p['session_date']==article['session_date']=='2022-09-01' and 'ESU22' in article['full_text']
page=json.loads((REC/'source-recovery-manifest.json').read_text());failed=[x for x in page['posts'] if x.get('capture_failed')]
assert len(failed)==1 and failed[0]['url']==p['url'] and len(failed[0]['attempts'])==2
assert all(x['http_status']==404 for x in failed[0]['attempts'])
for attempt in failed[0]['attempts']:
 b=(ROOT/attempt['path']).read_bytes();assert len(b)==attempt['bytes'] and hashlib.sha256(b).hexdigest()==attempt['sha256']
result={'status':'passed','scope':'Read-only separate retained2022context for an unavailable indexed archive locator; not recovery of the failed Wayback response or evidence of a2012plan.','canonical_url':p['url'],'failed_archived_source':failed[0]['archive_source_url'],'failed_archive_timestamp':failed[0]['archive_timestamp'],'failed_capture_attempts':failed[0]['attempts'],'retained_session_date':p['session_date'],'literal_title':p['title'],'source_capture_kind':p['capture_kind'],'captured_at':p.get('captured_at'),'source_capture_at':p.get('source_capture_at'),'retained_capture_manifest':ident(STAGE/'capture-manifest.json'),'retained_raw_html':{**ident(html),'uncompressed_bytes':len(raw),'uncompressed_sha256':hashlib.sha256(raw).hexdigest()},'retained_reader_capsule':q['capsule'],'retained_article_metadata':ident(meta),'normalized_full_body_sha256':hashlib.sha256(re.sub(r'\s+','',article['full_text']).encode()).hexdigest(),'literal_contract_tokens':sorted(set(re.findall(r'\b(?:ES|NQ|YM|RTY|CL|GC)[HMUZ]\d{1,2}\b',article['full_text']))),'failed_wayback_body_recovered':False,'historical_2012_identity_established':False,'qualification':'The successful2022 reader revision is byte-verified separately and retains its original capture clock. It does not establish what the failed2023Wayback snapshot contained and is not promoted into2012.'}
print(json.dumps(result,indent=2))
