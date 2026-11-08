import gzip, hashlib, json, xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
ROOT=Path('/Users/pruthvi/Documents/projects/abacus')
PRIOR=ROOT/'work/27_verniman_method_knowledge/20261031T141551Z_daily_maps_2016_r2'
REC=ROOT/'work/27_verniman_method_knowledge/20261031T155759Z_daily_maps_2011_recovery'
def sha(raw):return hashlib.sha256(raw).hexdigest()
def identity(path):
 raw=path.read_bytes();return {'path':str(path.relative_to(ROOT)),'bytes':len(raw),'sha256':sha(raw)}
def verify(base,record):
 path=(base/record['path']).resolve();path.relative_to(base.resolve());raw=path.read_bytes()
 assert len(raw)==record['bytes'] and sha(raw)==record['sha256'];return raw
capture=json.loads((PRIOR/'capture-manifest.json').read_text())
assert (PRIOR/'capture-manifest.json').read_bytes()==(ROOT/'runs/27_verniman_method_knowledge/20261031T141551Z_daily_maps_2016_r2/capture-manifest.json').read_bytes()
observations=json.loads(verify(PRIOR,capture['current_source_observations']))
inputs=[];locators=[];index_pages=[]
for record in observations['records']:
 if record.get('observation_kind')!='current_sitemap':continue
 raw=verify(PRIOR,record);xml=gzip.decompress(raw)
 assert len(xml)==record['uncompressed_bytes'] and sha(xml)==record['uncompressed_sha256']
 tree=ET.fromstring(xml)
 if tree.tag.endswith('sitemapindex'):index_pages=[e.text for e in tree.findall('{*}sitemap/{*}loc')]
 else:locators.extend(e.text for e in tree.findall('{*}url/{*}loc'))
 inputs.append({**identity(PRIOR/record['path']),'uncompressed_bytes':len(xml),'uncompressed_sha256':sha(xml),'url':record['url'],'captured_at':record['captured_at']})
assert len(inputs)==4 and set(index_pages)=={r['url'] for r in inputs[1:]}
assert len(locators)==2210 and len(set(locators))==2210
current=sorted(u for u in locators if '/2011/' in urlsplit(u).path)
assert len(current)==11
source=REC/'support/preflight/retained-sitemap-comparison.json';comparison=json.loads(source.read_text())
assert current==comparison['2011_current_locators'] and comparison['additional_current_locators']==3
index=REC/'index-01.json';rows=json.loads(index.read_text());header=rows[0]
canonical=set()
for row in rows[1:]:
 d=dict(zip(header,row));u=urlsplit(d['original']);assert u.hostname in {'verniman.blogspot.com','verniman.blogspot.com.ar'}
 canonical.add(urlunsplit(('https','verniman.blogspot.com',u.path,'','')))
extras=set(current)-canonical
assert len(canonical)==17 and len(set(current)&canonical)==8 and len(extras)==3
assert sorted(extras)==comparison['current_locators_absent_from_cdx']
supplement=REC/'support/current-sitemap-extra-posts.json'; extra_posts=json.loads(supplement.read_text())
assert {p['url'] for p in extra_posts}==extras
for p in extra_posts:
 assert p['source_format']=='current_html' and p['role']=='excluded_current_context' and p['session_date'] is None
 assert not any(k in p for k in ['archive_url','archive_timestamp','archive_observed_at','year_evidence'])
 verify(ROOT,p['html'])
 assert p['html']['http_status']==200 and p['html']['capture_kind']=='current_observation'
next_meta=json.loads((REC/'support/preflight/observed-feed-navigation.json').read_text())
next_urls=[]
for feed in sorted((REC/'support/preflight').glob('observed-blogger-atom-*.response.body')):
 tree=ET.fromstring(feed.read_bytes()); next_urls.extend(e.attrib['href'] for e in tree.findall('{http://www.w3.org/2005/Atom}link') if e.attrib.get('rel')=='next')
assert len(next_urls)==2 and len(set(next_urls))==1 and next_urls[0]=='http://www.blogger.com/feeds/6141192815370358651/posts/default?start-index=26&max-results=25'
assert json.loads((REC/'support/preflight/cdx-observed-feed-next-alltime.response.body').read_text())==[]
assert json.loads((REC/'support/preflight/available-observed-feed-next.response.body').read_text())['archived_snapshots']=={}
print(json.dumps({'status':'passed','scope':'Independent read-only retained sitemap/XML and bounded locator accounting; no source-year or historical completeness inference.','retained_observation_manifest':identity(PRIOR/capture['current_source_observations']['path']),'sitemap_inputs':inputs,'locator_count':len(locators),'current_2011_locators':len(current),'combined_cdx_canonical_paths':len(canonical),'additional_current_locators':len(extras),'current_locators_covered_by_cdx':8,'current_only_supplement':identity(supplement),'observed_feed_next':{'url':next_urls[0],'xml_occurrences':2,'cdx_rows':0,'available_snapshot':False},'historical_2011_identity_inferred_for_current_only':False,'source_comparison':identity(source),'combined_index':identity(index)},indent=2))
