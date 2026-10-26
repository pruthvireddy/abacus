# Presentation-only exporter for 07_range_xv_edge_candidates. No analytical imports.
SPEC = {'study_id': '07_range_xv_edge_candidates', 'source_run_id': '20260924T004900Z_rxv07', 'publication_id': '07-range-xv-edge-candidates-20261006-web', 'title': 'Range XV: three candidates fail the declared screen', 'summary': 'Three ES/NQ/GC chart-price candidates fail the frozen cost and familywise screen. Retrospectively inspected dates and unverified completion/fill timing limit trading claims.', 'selection': 'Registered reference', 'reason': 'Explicit registered reference; retain its executed scope and saved qualifications.', 'sources': ['report.md', 'manifest.json', 'inputs.lock.json', 'metrics.json', 'protocol-1.0.1.json'], 'sections': [{'kind': 'text', 'id': 'question', 'title': 'Question and scope', 'body': 'This study asks whether a one-bar pullback, an extended-run reversal, or a quiet-period breakout improves signed chart-price paths on ES 6RXV, NQ 20RXV and GC 20RXV. The selected run executed corrected protocol 1.0.1 on the pinned pre-normalization exports.', 'source': 'report.md', 'anchor': 'Question and scope'}, {'kind': 'text', 'id': 'findings', 'title': 'Supported findings', 'body': 'No primary idea-by-product comparison passes the declared screen. The selected all-history means below retain adverse tails and unsuccessful contrasts. Favorable point differences do not establish a candidate when uncertainty and later-block requirements fail.', 'source': 'report.md', 'anchor': 'Supported findings'}, {'kind': 'table', 'id': 'means', 'title': 'Primary all-history chart-price means', 'file': 'tables/primary_summary.csv', 'columns': [{'column': {'key': 'product', 'label': 'product'}, 'scale': 1}, {'column': {'key': 'idea', 'label': 'idea'}, 'scale': 1}, {'column': {'key': 'cohort', 'label': 'cohort'}, 'scale': 1}, {'column': {'key': 'horizon_bars', 'label': 'Future bars', 'format': 'number', 'precision': 0}, 'scale': 1}, {'column': {'key': 'opportunities', 'label': 'opportunities', 'format': 'number', 'precision': 0}, 'scale': 1}, {'column': {'key': 'trades', 'label': 'Executed proxy trades', 'format': 'number', 'precision': 0}, 'scale': 1}, {'column': {'key': 'mean_ticks', 'label': 'Gross mean', 'format': 'number', 'precision': 2, 'unit': 'ticks'}, 'scale': 1}, {'column': {'key': 'mean_net_2_ticks', 'label': 'Mean after haircut', 'format': 'number', 'precision': 2, 'unit': 'ticks'}, 'scale': 1}, {'column': {'key': 'p05_ticks', 'label': '5th percentile', 'format': 'number', 'precision': 2, 'unit': 'ticks'}, 'scale': 1}], 'where': {'split': ['all'], 'cohort': ['extreme_break', 'wait_policy', 'quiet']}, 'description': 'All-history selected primary candidate policies, all three products'}, {'kind': 'table', 'id': 'contrasts', 'title': 'Candidate minus its declared control', 'file': 'tables/primary_contrasts.csv', 'columns': [{'column': {'key': 'product', 'label': 'product'}, 'scale': 1}, {'column': {'key': 'idea', 'label': 'idea'}, 'scale': 1}, {'column': {'key': 'candidate', 'label': 'candidate'}, 'scale': 1}, {'column': {'key': 'control', 'label': 'control'}, 'scale': 1}, {'column': {'key': 'n_sessions', 'label': 'Session clusters', 'format': 'number', 'precision': 0}, 'scale': 1}, {'column': {'key': 'difference_ticks', 'label': 'Difference', 'format': 'number', 'precision': 2, 'unit': 'ticks'}, 'scale': 1}, {'column': {'key': 'lower', 'label': 'Familywise low', 'format': 'number', 'precision': 2, 'unit': 'ticks'}, 'scale': 1}, {'column': {'key': 'upper', 'label': 'Familywise high', 'format': 'number', 'precision': 2, 'unit': 'ticks'}, 'scale': 1}], 'where': {'split': ['all']}, 'description': 'All saved rows'}, {'kind': 'text', 'id': 'methods', 'title': 'Definitions and methods', 'body': 'Pullback uses a completed return bar after one opposing bar and measures one future bar against all unfiltered snapbacks. Exhaustion compares a wait-for-second-reversal policy with the early policy on every original opportunity, using three future bars. Quiet breakout uses a low prior thirty-minute bar count and a two-bar extreme break, against the same breakout without low activity. Entry and exit are next-bar open references; wait opportunities without confirmation contribute zero and incur no assumed cost. Net deducts two ticks per executed round trip. The contrast interval is the saved 99.44% session-cluster familywise interval for nine comparisons.', 'source': 'protocol-1.0.1.json', 'anchor': 'Definitions and methods'}, {'kind': 'text', 'id': 'limitations', 'title': 'Limitations and uncertainty', 'body': 'All dates were retrospectively inspected. Completion is only a next-bar-start proxy; timezone, intrabar order, bid/ask and fills are unverified. The run used older export-clock inputs; later clock correction does not change this sealed cohort or its quiet-period calibration. Assumed tick haircuts do not establish executable net profitability.', 'source': 'report.md', 'anchor': 'Limitations and uncertainty'}]}
EXPECTED = {'runs/07_range_xv_edge_candidates/20260924T004900Z_rxv07/manifest.json': '2c83543e8e07cefeb074afff5af1e0c135c481efdf6d27575cf81f5ee3e04f9d', 'runs/07_range_xv_edge_candidates/20260924T004900Z_rxv07/tables/primary_summary.csv': '8940a2557450327b8d61b131fade80146cfdf261cef4d1664b86d60c79d72e67', 'runs/07_range_xv_edge_candidates/20260924T004900Z_rxv07/report.md': '114a8b77b86d7f8d1227e668111a2ef4058fd0b7ece0ccf8f2c4fab8591fa593', 'runs/07_range_xv_edge_candidates/20260924T004900Z_rxv07/metrics.json': '5bc9b6f95b7264617bf9a9c9dd9fd8eea28993f82713bda79156917daf9071fa', 'runs/07_range_xv_edge_candidates/20260924T004900Z_rxv07/inputs.lock.json': '0601e21a2198ded7acadeefe46bb510fbf462b42c4c8704c1417dad31a95c57a', 'runs/07_range_xv_edge_candidates/20260924T004900Z_rxv07/tables/primary_contrasts.csv': 'e1796adb42a1d63d37adbb962132bee532628dd485daf0e89d3267993cc4f5e6', 'runs/07_range_xv_edge_candidates/20260924T004900Z_rxv07/protocol-1.0.1.json': '831d15616cedd3170252a6281765aecb9fcbca212c56b42f256a21ca54153188'}

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
