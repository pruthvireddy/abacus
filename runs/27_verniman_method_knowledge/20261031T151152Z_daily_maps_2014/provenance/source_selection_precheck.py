#!/usr/bin/env python3
"""Independent raw-source membership, overlap and selected-source precheck."""
import hashlib,importlib.util,json,re,sys
from collections import Counter,defaultdict
from datetime import date
from pathlib import Path
from urllib.parse import urljoin
sys.dont_write_bytecode=True
ROOT=Path('/Users/pruthvi/Documents/projects/abacus')
REC=ROOT/'work/27_verniman_method_knowledge/20261031T151152Z_daily_maps_2014_recovery'
spec=importlib.util.spec_from_file_location('independent_source_parser_2014',Path('/private/tmp/verniman-2014-audit-capture.py'));parser=importlib.util.module_from_spec(spec);spec.loader.exec_module(parser)
def digest(raw):return hashlib.sha256(raw).hexdigest()
def key(parts):return re.sub(r'\s+','',''.join(parts))
checked={}
def read(r):
 p=(ROOT/r['path']).resolve();p.relative_to(ROOT);raw=p.read_bytes();assert len(raw)==r['bytes'] and digest(raw)==r['sha256'],str(p);checked[str(p)]=r['sha256'];return raw
raw=(REC/'recovery-manifest.json').read_bytes();manifest=json.loads(raw);posts=manifest['posts'];assert len(posts)==94
for r in manifest['files']:read(r)
rows=[];groups=defaultdict(list);contexts=[]
for ordinal,p in enumerate(posts,1):
 fmt=p['source_format']; source=p['atom'] if fmt=='archived_atom_feed' else p['html'];original=read(source)
 if fmt=='archived_atom_feed':
  body=parser.atom_source(original,p);bodies=[body];read(p['entry_record'])
 else:
  h=parser.Bodies();h.feed(original.decode('utf-8','replace'));bodies=h.rows
  body=parser.html_source(original,p) if len(bodies)==1 else None
 read(p['post_record'])
 assert len(bodies)==p['post_body_count'] if 'post_body_count' in p else True
 if body:
  assert ' '.join(body['title'].split())==' '.join(p['title'].split())
  assert key(body['parts'])==key([p['body_text']])
 imgs=[im for b in bodies for im in b['images']];assert len(imgs)==len(p['images']),('actual image element count',ordinal)
 for im,saved,actual in zip(imgs,p['images'],p['actual_image_elements']):
  inline=urljoin(p['url'],im['inline']);linked=urljoin(p['url'],im['linked']) if im['linked'] else inline
  preferred=linked if re.search(r'(?:blogger\.googleusercontent\.com|bp\.blogspot\.com)/',linked) else inline
  assert saved['original_image_url']==preferred and actual['url']==preferred and actual['inline_url']==inline
  assert saved['kind']=='current_source_image_fallback' and saved['historical_digest_match_verified'] is False
  read(saved)
 title=p['title'];primary=body is not None and bool(re.fullmatch(r'(?:Opening(?:\s+Print)?(?:\s+\d{4})?|Market\s+Update\s+(?:0603|0825)|Update\s+\d{4})',title))
 summary={'ordinal':ordinal,'source_post_id':p.get('source_post_id'),'title':title,'url':p['url'],'source_format':fmt,'source_sha256':source['sha256'],'post_record':p['post_record'],'body_count':len(bodies),'body_identities':[{'source_post_id':b['id'],'title':b['title'],'normalized_body_sha256':digest(key(b['parts']).encode()),'images':len(b['images']),'ordered_body_links_sha256':digest(json.dumps(b['links'],ensure_ascii=False,separators=(',',':')).encode())} for b in bodies],'image_references':len(imgs),'candidate_primary':primary}
 if primary:
  prose=' '.join(''.join(body['parts']).split()).lower();assert 'overnight inventory' in prose and any(x in prose for x in ['open auction','open drive','balanced open','morning after trend']), (ordinal,title,prose)
  match=re.search(r'\b(\d{2})(\d{2})\b',title);stamp=date(2014,int(match[1]),int(match[2])).isoformat() if match else None
  if stamp is None:assert title=='Opening Print'
  summary.update(session_date=stamp,normalized_body_sha256=digest(key(body['parts']).encode()))
  groups[str(p['source_post_id'])].append((p,body,summary))
 else:
  if not bodies:reason='Observed index response contains no post-body elements; no daily source is inferred.'
  elif len(bodies)>1:reason='Every actual body inspected: educational/platform material; no supported 2014 daily morning plan.'
  elif p.get('source_post_id')=='2063013809007880904':reason='Actual body is stale 2022 Outlook06/21 with ESU22 and2022Fed context; URL2014 does not establish year.'
  elif title in {'Market Update','$ES_F Update','Closing Print'}:reason='Image-only update/closing material lacks a supported dated prospective morning-plan identity; chart inspection does not establish exact day or role. Retained raw without inferring image-filename timing.'
  else:reason='Educational, platform, psychology or general market-method source, not a dated morning plan.'
  summary['exclusion_reason']=reason;contexts.append(summary)
 rows.append(summary)
selected=[];overlaps=[]
for identifier,versions in groups.items():
 def priority(v):
  p=v[0];return (0 if p['source_format']=='archived_html' else 1 if p['source_format']=='archived_page_post' else 2,0 if p['title'].startswith('Opening') else 1)
 versions=sorted(versions,key=priority);p,b,s=versions[0];selected.append(s)
 for op,ob,os in versions[1:]:
  compare={'post_id_equal':p['source_post_id']==op['source_post_id'],'normalized_full_text_equal':key(b['parts'])==key(ob['parts']),'ordered_body_links_equal':b['links']==ob['links'],'ordered_image_elements_equal':b['images']==ob['images'],'retained_image_hashes_equal':[i['sha256'] for i in p['images']]==[i['sha256'] for i in op['images']]};assert all(compare.values()),(identifier,compare)
  titles_equal=p['title']==op['title'];assert titles_equal or identifier in {'5869751996151420272','2809509541878771684'}
  overlaps.append({'source_post_id':identifier,'primary':s,'supporting_revision':os,'literal_titles_equal':titles_equal,'qualification':'Earlier Update title changes to Opening in later exact Atom revision; both raw titles retained.' if not titles_equal else 'Literal title and complete selected content match.','comparisons':compare})
selected.sort(key=lambda s:(s['session_date'] or '',s['url']),reverse=True)
images=[im for s in selected for im in posts[s['ordinal']-1]['images']];dates=[s['session_date'] for s in selected if s['session_date']];assert len(dates)==len(set(dates))
result={'status':'passed','scope':'Independent actual raw-body membership and complete-image/overlap verification; not a historical completeness or availability claim.','recovery_manifest':{'path':str((REC/'recovery-manifest.json').relative_to(ROOT)),'bytes':len(raw),'sha256':digest(raw)},'checked_unique_files':len(checked),'raw_source_revisions':len(posts),'raw_primary_candidates':sum(len(v) for v in groups.values()),'selected_records':len(selected),'dated_maps':len(dates),'distinct_dated_days':len(set(dates)),'undated_daily_plans':sum(s['session_date'] is None for s in selected),'date_range':[min(dates),max(dates)],'source_formats':dict(Counter(s['source_format'] for s in selected)),'image_references':len(images),'unique_image_hashes':len({im['sha256'] for im in images}),'unselected_supporting_revisions':len(overlaps),'excluded_context_records':len(contexts),'multi_body_context_records':sum(s['body_count']>1 for s in contexts),'zero_body_index_records':sum(s['body_count']==0 for s in contexts),'selected_sources':selected,'overlap_comparisons':overlaps,'excluded_contexts':contexts,'historical_full_year_completeness_claimed':False,'lower_boundary_observed':False}
assert result['selected_records']==37 and result['dated_maps']==35 and result['undated_daily_plans']==2 and result['image_references']==111
print(json.dumps(result,indent=2))
