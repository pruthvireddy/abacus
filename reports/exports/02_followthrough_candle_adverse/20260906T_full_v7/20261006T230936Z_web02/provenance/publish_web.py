# Presentation-only exporter for 02_followthrough_candle_adverse. No analytical imports.
SPEC = {'study_id': '02_followthrough_candle_adverse', 'source_run_id': '20260906T_full_v7', 'publication_id': '02-followthrough-candle-adverse-20261006-web', 'title': 'Follow-through candle: conditional adverse movement', 'summary': 'Saved candle geometry estimates condition on eventual same-direction closes. Corrected complete-leg duration is a raw clock proxy; neither result is a live entry filter.', 'selection': 'Publication-only choice', 'reason': 'full_v7 contains the explicitly corrected complete-leg duration alongside original second-candle geometry. The corrected definition, not timestamp recency, determines this publication selection.', 'sources': ['report.md', 'run_manifest.json', 'import_manifest.json', 'methodology.md', 'data_quality.md'], 'sections': [{'kind': 'text', 'id': 'question', 'title': 'Question and scope', 'body': 'For a reversal whose immediately following candle eventually closes in its direction, how far does that second candle move adversely from its own open? The retained full_v7 import also contains the corrected duration of complete reversal legs including the reversal.', 'source': 'report.md', 'anchor': 'Question and scope'}, {'kind': 'text', 'id': 'findings', 'title': 'Supported findings', 'body': 'Larger range settings generally allow larger adverse movement in the successful second candle. Duration summaries condition on complete legs with at least three candles and retain tied-clock zero duration. These are conditional descriptions of geometry and completed paths, not causal filters or trading performance.', 'source': 'report.md', 'anchor': 'Supported findings'}, {'kind': 'table', 'id': 'geometry', 'title': 'Conditional second-candle geometry, all charts', 'file': 'tables/headline.csv', 'columns': [{'column': {'key': 'asset', 'label': 'asset'}, 'scale': 1}, {'column': {'key': 'range_setting', 'label': 'Range XV setting', 'format': 'number', 'precision': 0}, 'scale': 1}, {'column': {'key': 'eligible_next_bar', 'label': 'Eligible next bars', 'format': 'number', 'precision': 0}, 'scale': 1}, {'column': {'key': 'same_direction_next_bar', 'label': 'Same-direction closes', 'format': 'number', 'precision': 0}, 'scale': 1}, {'column': {'key': 'same_direction_probability', 'label': 'Success rate', 'format': 'percent', 'precision': 1}, 'scale': 1}, {'column': {'key': 'denominator', 'label': 'Conditioned geometry n', 'format': 'number', 'precision': 0}, 'scale': 1}, {'column': {'key': 'mean_adverse_ticks', 'label': 'Mean adverse', 'format': 'number', 'precision': 2, 'unit': 'ticks'}, 'scale': 1}, {'column': {'key': 'mean_adverse_ci_low_ticks', 'label': '95% mean low', 'format': 'number', 'precision': 2, 'unit': 'ticks'}, 'scale': 1}, {'column': {'key': 'mean_adverse_ci_high_ticks', 'label': '95% mean high', 'format': 'number', 'precision': 2, 'unit': 'ticks'}, 'scale': 1}, {'column': {'key': 'median_adverse_ticks', 'label': 'Median adverse', 'format': 'number', 'precision': 2, 'unit': 'ticks'}, 'scale': 1}, {'column': {'key': 'p90_adverse_ticks', 'label': '90th percentile', 'format': 'number', 'precision': 2, 'unit': 'ticks'}, 'scale': 1}], 'where': {}, 'description': 'All saved rows'}, {'kind': 'table', 'id': 'duration', 'title': 'Corrected full-leg duration proxy', 'file': 'tables/leg_duration_summary.csv', 'columns': [{'column': {'key': 'asset', 'label': 'asset'}, 'scale': 1}, {'column': {'key': 'range_setting', 'label': 'range setting', 'format': 'number', 'precision': 0}, 'scale': 1}, {'column': {'key': 'completed_legs', 'label': 'Complete legs', 'format': 'number', 'precision': 0}, 'scale': 1}, {'column': {'key': 'censored_legs', 'label': 'Censored legs', 'format': 'number', 'precision': 0}, 'scale': 1}, {'column': {'key': 'legs_at_least_three', 'label': 'Qualified complete legs', 'format': 'number', 'precision': 0}, 'scale': 1}, {'column': {'key': 'mean_duration_proxy_minutes', 'label': 'Mean duration', 'format': 'number', 'precision': 2, 'unit': 'minutes'}, 'scale': 1}, {'column': {'key': 'mean_duration_ci_low_minutes', 'label': '95% low', 'format': 'number', 'precision': 2, 'unit': 'minutes'}, 'scale': 1}, {'column': {'key': 'mean_duration_ci_high_minutes', 'label': '95% high', 'format': 'number', 'precision': 2, 'unit': 'minutes'}, 'scale': 1}, {'column': {'key': 'median_duration_proxy_minutes', 'label': 'Median', 'format': 'number', 'precision': 2, 'unit': 'minutes'}, 'scale': 1}, {'column': {'key': 'zero_duration_count', 'label': 'Tied-clock zeros', 'format': 'number', 'precision': 0}, 'scale': 1}], 'where': {}, 'description': 'All saved rows'}, {'kind': 'text', 'id': 'methods', 'title': 'Definitions and methods', 'body': 'Second-candle adverse movement is own-open minus low for a bullish reversal, high minus own-open for bearish. The geometry denominator includes only eventual same-direction second candles; the eligible-next-bar count and success rate expose selection. Complete leg duration includes the reversal and all same-colour successors through the last one, excluding right-censored legs. Its clock difference is a proxy; zero is observed tied timestamps and missing remains null. Saved 95% intervals use export-date cluster draws. Native units are product ticks for movement and minutes for duration; GC 6 is included as labelled and does not substitute for missing GC 20.', 'source': 'report.md', 'anchor': 'Definitions and methods'}, {'kind': 'text', 'id': 'limitations', 'title': 'Limitations and uncertainty', 'body': 'Historical import was not newly revalidated; original short-export inputs are missing. Bar open/close timing, timezone, session boundaries and provisional chart identity remain unverified. Conditioning on the future candle close is not an observable real-time entry rule. Window rankings and same-sample selections are excluded here; no stop ordering, fills, costs or profitability are established.', 'source': 'report.md', 'anchor': 'Limitations and uncertainty'}]}
EXPECTED = {'runs/02_followthrough_candle_adverse/20260906T_full_v7/import_manifest.json': '9c515b597cc0e99d93411a0636150415ccd808ea44fcb04e94977dc9df79f3e7', 'runs/02_followthrough_candle_adverse/20260906T_full_v7/report.md': '9670b8dceb9fc86c36da9cd39fa380c076de5d4db837c2e504b185ca30bfc24a', 'runs/02_followthrough_candle_adverse/20260906T_full_v7/tables/headline.csv': 'e906d78f84e592f20e3117fa066b52017a254e49fe5ffc411c32a0f67de91543', 'runs/02_followthrough_candle_adverse/20260906T_full_v7/data_quality.md': '92e4c77919b79d868d35635c645df08727a027e64a10a0c46305ec2ce62e88ec', 'runs/02_followthrough_candle_adverse/20260906T_full_v7/methodology.md': 'a5d1be3eee4c528c7739c72cee40482994a61033655231f92293c1d92e8e621d', 'runs/02_followthrough_candle_adverse/20260906T_full_v7/tables/leg_duration_summary.csv': 'c4081e6afbcb1d5e68544b8e8dd3f3accdd9e0126481622ddb5e68ec855e0eca', 'runs/02_followthrough_candle_adverse/20260906T_full_v7/run_manifest.json': '623e977bd657bbdf9c19b3079978e4b610003df43fcc6a3dab98e2f7bc309ffc'}

import argparse,csv,hashlib,json,math,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def transfer(raw,column,scale):
 if raw=='':return None
 if column.get('format'):
  value=float(raw)*scale
  assert math.isfinite(value)
  return value
 if raw in ['True','False']:return raw=='True'
 return raw.replace('_',' ') if column['key'] not in ['metric_id','metric_id_departure','metric_id_touch'] else raw

def prepare(revision):
 run=ROOT/'runs'/SPEC['study_id']/SPEC['source_run_id']
 bindings=[];sections=[];sources=set(SPEC['sources']);claims=[]
 for item in SPEC['sections']:
  if item['kind']=='text':
   sections.append({k:item[k] for k in ['kind','id','title','body']})
   sources.add(item['source']);claims.append({'section':item['id'],'source':str((run/item['source']).relative_to(ROOT)),'heading_or_scope': {'scope': 'Selected saved document; authored abridgment', 'headings': [line.lstrip('#').strip() for line in (run/item['source']).read_text().splitlines() if line.startswith('#')]},'operation':'Authored abridgment preserving the saved meaning; definitions and result numbers are not recomputed.'})
  else:
   sources.add(item['file']);rows=list(csv.DictReader((run/item['file']).open()))
   chosen=[(i,row) for i,row in enumerate(rows,1) if all(row[k] in values for k,values in item['where'].items())]
   assert chosen and len(chosen)<=100,(item['id'],len(chosen))
   output=[]
   for source_row,row in chosen:
    target={}
    for field in item['columns']:
     c=field['column'];k=c['key'];target[k]=transfer(row[k],c,field['scale'])
     bindings.append({'section':item['id'],'output_row':len(output),'column':k,'source':str((run/item['file']).relative_to(ROOT)),'data_row_1_based':source_row,'source_column':k,'source_raw':row[k],'scale':field['scale'],'value':target[k]})
    output.append(target)
   sections.append({'kind':'table','id':item['id'],'title':item['title'],'columns':[f['column'] for f in item['columns']],'rows':output})
 provenance=f"Study {SPEC['study_id']}; source run {SPEC['source_run_id']}. {SPEC['selection']}: {SPEC['reason']}\n\nPresentation revision {revision}, web-study-report-1.0. Saved numerical tables are the authority; only selected rows and columns are presented. No new statistics or research execution. The publication record identifies this JSON and its selected assets."
 sections.append({'kind':'text','id':'sources-provenance','title':'Source and presentation provenance','body':provenance})
 pub={'schemaVersion':'1.0','id':SPEC['publication_id'],'title':SPEC['title'],'summary':SPEC['summary'],'publishedAt':'2026-10-06T23:09:36Z','source':{'producer':'sahadeva','runId':SPEC['source_run_id']},'sections':sections}
 artifacts=[]
 for name in sorted(sources):
  p=run/name;relative=str(p.relative_to(ROOT));assert digest(p)==EXPECTED[relative],relative
  artifacts.append({'path':relative,'sha256':digest(p)})
 return pub,{'study_id':SPEC['study_id'],'source_run_id':SPEC['source_run_id'],'revision_id':revision,'sources':artifacts,'bindings':bindings,'claims':claims,'table_selections':[{'section':i['id'],'source':i['file'],'where':i['where'],'description':i['description']} for i in SPEC['sections'] if i['kind']=='table'],'figures':[]}

if __name__=='__main__':
 parser=argparse.ArgumentParser(description='Presentation only: select pinned saved evidence; never execute research.')
 parser.add_argument('--revision',required=True);parser.add_argument('--check',action='store_true');args=parser.parse_args()
 assert __import__('re').fullmatch(r'[A-Za-z0-9_-]+',args.revision)
 out=ROOT/'reports/exports'/SPEC['study_id']/SPEC['source_run_id']/args.revision
 pub,mapping=prepare(args.revision)
 if args.check:
  assert json.loads((out/'publication.json').read_text())==pub
  assert json.loads((out/'source-map.json').read_text())==mapping
  print(f"{SPEC['study_id']}: {len(mapping['bindings'])} saved-cell transfers and source hashes match.")
 else:
  out.mkdir(parents=True,exist_ok=False)
  for name,value in [('publication.json',pub),('source-map.json',mapping)]:
   (out/name).write_text(json.dumps(value,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
  (out/'provenance').mkdir();shutil.copyfile(__file__,out/'provenance/publish_web.py')
  (out/'README.md').write_text(f"# {SPEC['title']}\n\n[Publication](publication.json) · [Source map](source-map.json) · [Manifest](manifest.json) · [Verification](verification.json)\n\n{SPEC['selection']}: {SPEC['reason']}\n\nBounded table-first presentation. Full tables and research figures remain in the saved run. No new calculations. Reproduce into a fresh revision and use a fresh publication ID for changed content.\n")
  print(out.relative_to(ROOT))
