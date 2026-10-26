# Presentation-only exporter for 04_reversal_candle_quality. No analytical imports.
SPEC = {'study_id': '04_reversal_candle_quality', 'source_run_id': '20260908T_reversal_quality_v1', 'publication_id': '04-reversal-candle-quality-20261006-web', 'title': 'Reversal quality: colour advantage, negative payoff', 'summary': 'Aligned strong candles show a next-bar colour advantage that weakens over longer runs. Saved mean next-bar returns remain negative before costs, despite high continuation rates.', 'selection': 'Publication-only choice', 'reason': 'Sole retained candle-quality follow-up directly covers the question and preserves the negative price diagnostic. Historical and provenance limitations remain explicit; no research reference is created.', 'sources': ['summary.md', 'run_manifest.json', 'import_manifest.json', 'methodology.md'], 'sections': [{'kind': 'text', 'id': 'question', 'title': 'Question and scope', 'body': 'Does reversal candle quality add to strictly prior larger-chart alignment? The retained historical run compares quality-stack candles and one-bar failed pullbacks across ES 5→6, GC 6→10, NQ 10→20 and secondary GC 10→20.', 'source': 'summary.md', 'anchor': 'Question and scope'}, {'kind': 'text', 'id': 'findings', 'title': 'Supported findings', 'body': 'Quality-stack alignment improves next-bar colour persistence more consistently than longer runs. A break of the full prior run largely identifies the one-bar pullback structure rather than an independent candle factor. The saved price means are negative before fees and slippage: larger failures outweigh frequent small colour successes.', 'source': 'summary.md', 'anchor': 'Supported findings'}, {'kind': 'table', 'id': 'quality', 'title': 'Aligned quality stack: colour and next-bar price', 'file': 'tables/continuation_feature_contrasts.csv', 'columns': [{'column': {'key': 'pair_id', 'label': 'pair id'}, 'scale': 1}, {'column': {'key': 'outcome', 'label': 'outcome'}, 'scale': 1}, {'column': {'key': 'feature_n', 'label': 'Quality eligible n', 'format': 'number', 'precision': 0}, 'scale': 1}, {'column': {'key': 'nonfeature_n', 'label': 'Other eligible n', 'format': 'number', 'precision': 0}, 'scale': 1}, {'column': {'key': 'feature_rate', 'label': 'Quality rate', 'format': 'percent', 'precision': 1}, 'scale': 1}, {'column': {'key': 'nonfeature_rate', 'label': 'Other rate', 'format': 'percent', 'precision': 1}, 'scale': 1}, {'column': {'key': 'feature_minus_nonfeature', 'label': 'Rate difference', 'format': 'number', 'precision': 1, 'unit': 'pp'}, 'scale': 100}, {'column': {'key': 'cluster_bootstrap_ci_low', 'label': '95% difference low', 'format': 'number', 'precision': 1, 'unit': 'pp'}, 'scale': 100}, {'column': {'key': 'cluster_bootstrap_ci_high', 'label': '95% difference high', 'format': 'number', 'precision': 1, 'unit': 'pp'}, 'scale': 100}, {'column': {'key': 'feature_mean_forward_return_ticks', 'label': 'Quality mean next-bar return', 'format': 'number', 'precision': 2, 'unit': 'ticks'}, 'scale': 1}, {'column': {'key': 'nonfeature_mean_forward_return_ticks', 'label': 'Other mean next-bar return', 'format': 'number', 'precision': 2, 'unit': 'ticks'}, 'scale': 1}], 'where': {'split': ['test'], 'timing_sample': ['strict'], 'context': ['aligned'], 'direction': ['both'], 'feature': ['quality_stack']}, 'description': 'All saved rows'}, {'kind': 'table', 'id': 'snapback', 'title': 'Aligned one-bar pullback versus longer prior runs', 'file': 'tables/one_bar_snapback_contrasts.csv', 'columns': [{'column': {'key': 'pair_id', 'label': 'pair id'}, 'scale': 1}, {'column': {'key': 'outcome', 'label': 'outcome'}, 'scale': 1}, {'column': {'key': 'one_bar_n', 'label': 'one bar n', 'format': 'number', 'precision': 0}, 'scale': 1}, {'column': {'key': 'longer_n', 'label': 'longer n', 'format': 'number', 'precision': 0}, 'scale': 1}, {'column': {'key': 'one_bar_prior_run_rate', 'label': 'one bar prior run rate', 'format': 'percent', 'precision': 1}, 'scale': 1}, {'column': {'key': 'longer_prior_run_rate', 'label': 'longer prior run rate', 'format': 'percent', 'precision': 1}, 'scale': 1}, {'column': {'key': 'one_bar_minus_longer', 'label': 'Rate difference', 'format': 'number', 'precision': 1, 'unit': 'pp'}, 'scale': 100}, {'column': {'key': 'cluster_bootstrap_ci_low', 'label': '95% low', 'format': 'number', 'precision': 1, 'unit': 'pp'}, 'scale': 100}, {'column': {'key': 'cluster_bootstrap_ci_high', 'label': '95% high', 'format': 'number', 'precision': 1, 'unit': 'pp'}, 'scale': 100}], 'where': {'split': ['test'], 'context': ['aligned']}, 'description': 'All saved rows'}, {'kind': 'text', 'id': 'methods', 'title': 'Definitions and methods', 'body': 'Quality stack requires body at least seventy percent of high-low range, favorable close within the final twenty percent, and a break of the previous bar directional extreme. The larger state must complete strictly before the small signal; same-second ambiguity is excluded. L excludes the reversal. The test-labelled April–September 2026 contrasts use saved 95% session-cluster pointwise intervals and do not correct a feature search. The next-bar-close price diagnostic is measured in small-chart product ticks; it is not the colour probability. One-bar snapback compares exactly one opposing prior bar with longer prior runs.', 'source': 'summary.md', 'anchor': 'Definitions and methods'}, {'kind': 'text', 'id': 'limitations', 'title': 'Limitations and uncertainty', 'body': 'Historical import is not newly validated execution evidence. Inputs and modern code/environment provenance are incomplete; chart clocks, completion and fills remain unverified. Longer-horizon and exhaustion interactions are weak or unstable. Shared chart settings and earlier study inspection limit independence. OHLC cannot establish stop/target order, and hypothetical stops must not be inferred to repair the negative payoff.', 'source': 'summary.md', 'anchor': 'Limitations and uncertainty'}]}
EXPECTED = {'runs/04_reversal_candle_quality/20260908T_reversal_quality_v1/import_manifest.json': 'f4440f1d223639dda7b13bd0fdbd315f60168775d7936f38bbef8dd849814384', 'runs/04_reversal_candle_quality/20260908T_reversal_quality_v1/summary.md': '82817885c71d292d37bbbf9e237a5eea0f0f2024784eeb26467661342ce66f68', 'runs/04_reversal_candle_quality/20260908T_reversal_quality_v1/tables/one_bar_snapback_contrasts.csv': 'e77e7de4e956574a919a33d74767591660c28c83490d896b2a0494dbab321d6d', 'runs/04_reversal_candle_quality/20260908T_reversal_quality_v1/tables/continuation_feature_contrasts.csv': 'bca225d8c3203d5af4a5715d84e5695cf6462e73f50d4814a659d47a70bce898', 'runs/04_reversal_candle_quality/20260908T_reversal_quality_v1/methodology.md': 'd493cbfacfd60ce4f6c7253a94f4700a3adae16c035cabf448bb2041decb50da', 'runs/04_reversal_candle_quality/20260908T_reversal_quality_v1/run_manifest.json': 'f31075cbe4d9375433e3db7d8e478db12459bae15f82b7ebfed4bc273c598fb1'}

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
