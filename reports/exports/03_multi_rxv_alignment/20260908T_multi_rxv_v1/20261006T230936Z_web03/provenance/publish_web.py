# Presentation-only exporter for 03_multi_rxv_alignment. No analytical imports.
SPEC = {'study_id': '03_multi_rxv_alignment', 'source_run_id': '20260908T_multi_rxv_v1', 'publication_id': '03-multi-rxv-alignment-20261006-web', 'title': 'Chart alignment: stronger next-bar persistence', 'summary': 'Strictly prior larger-chart alignment improves next-bar colour continuation most consistently in ES and GC. Longer runs are less stable; shared price streams limit independence.', 'selection': 'Publication-only choice', 'reason': 'Sole retained direct-question run; strict-timing evidence and explicit limitations make it usable for a qualified historical presentation, without registering a research reference.', 'sources': ['summary.md', 'run_manifest.json', 'import_manifest.json', 'methodology.md'], 'sections': [{'kind': 'text', 'id': 'question', 'title': 'Question and scope', 'body': 'Does a small Range XV reversal aligned with the latest strictly prior completed larger bar persist more than one opposing it? Primary pairs are ES 5→6, GC 6→10 and NQ 10→20; GC 10→20 is secondary. Requested ES 4 pairing is absent.', 'source': 'summary.md', 'anchor': 'Question and scope'}, {'kind': 'text', 'id': 'findings', 'title': 'Supported findings', 'body': 'Alignment has clearer next-bar differences than sustained three-/five-bar continuation. Confirmation examples reuse the same trades and are not independent early-versus-late execution comparisons. The selected table retains adverse and inconclusive contrasts rather than only positive pairs.', 'source': 'summary.md', 'anchor': 'Supported findings'}, {'kind': 'table', 'id': 'alignment', 'title': 'Test-labelled strict alignment contrasts', 'file': 'tables/aligned_vs_countertrend.csv', 'columns': [{'column': {'key': 'pair_id', 'label': 'Small → large chart pair'}, 'scale': 1}, {'column': {'key': 'outcome', 'label': 'outcome'}, 'scale': 1}, {'column': {'key': 'aligned_n', 'label': 'Aligned eligible n', 'format': 'number', 'precision': 0}, 'scale': 1}, {'column': {'key': 'countertrend_n', 'label': 'Opposing eligible n', 'format': 'number', 'precision': 0}, 'scale': 1}, {'column': {'key': 'aligned_rate', 'label': 'aligned rate', 'format': 'percent', 'precision': 1}, 'scale': 1}, {'column': {'key': 'countertrend_rate', 'label': 'Opposing rate', 'format': 'percent', 'precision': 1}, 'scale': 1}, {'column': {'key': 'aligned_minus_countertrend', 'label': 'Aligned minus opposing', 'format': 'number', 'precision': 1, 'unit': 'pp'}, 'scale': 100}, {'column': {'key': 'cluster_bootstrap_ci_low', 'label': '95% difference low', 'format': 'number', 'precision': 1, 'unit': 'pp'}, 'scale': 100}, {'column': {'key': 'cluster_bootstrap_ci_high', 'label': '95% difference high', 'format': 'number', 'precision': 1, 'unit': 'pp'}, 'scale': 100}], 'where': {'split': ['test'], 'timing_sample': ['strict'], 'direction': ['both']}, 'description': 'All saved rows'}, {'kind': 'text', 'id': 'methods', 'title': 'Definitions and methods', 'body': 'L counts additional same-colour followers after the small reversal. Larger state must complete strictly before the small signal next-bar-start proxy in the same inferred session; equal-second joins are excluded. Test-labelled rows cover April 13–September 8, 2026, following development August 2024–November 2025 and validation through April 10, 2026. Both directions are the saved combined descriptive cohort. Saved 95% intervals cluster by inferred session; rate differences and their interval bounds are converted from ratios to percentage points without recalculation.', 'source': 'summary.md', 'anchor': 'Definitions and methods'}, {'kind': 'text', 'id': 'limitations', 'title': 'Limitations and uncertainty', 'body': 'This historical import is unreviewed during consolidation; saved provenance lacks a modern code/environment seal; original input locators are recorded separately from the presented artifact hashes. Timezone and 18:00 session interpretation are inferred. Paired settings share underlying trades. Test labels do not establish pristine confirmation or verified completion. No costs, fills or deployable trading edge are shown.', 'source': 'summary.md', 'anchor': 'Limitations and uncertainty'}]}
EXPECTED = {'runs/03_multi_rxv_alignment/20260908T_multi_rxv_v1/import_manifest.json': '48272cedd83438029e86692ccd9fb6c616bb6b78c3d8e98f0edda488c4e030d6', 'runs/03_multi_rxv_alignment/20260908T_multi_rxv_v1/summary.md': '7645768c66a8a56a7bc096a48aae5b91c89725cabe3727ffa5e2c73a43e2e5c6', 'runs/03_multi_rxv_alignment/20260908T_multi_rxv_v1/tables/aligned_vs_countertrend.csv': 'dd878071127db6105260347c9cf9b51a02780c88a8f573832773047847a73540', 'runs/03_multi_rxv_alignment/20260908T_multi_rxv_v1/methodology.md': '4b4a47e5431fa16bba553b2d7f6c923607f557ee5a60f6a831dd980daf178854', 'runs/03_multi_rxv_alignment/20260908T_multi_rxv_v1/run_manifest.json': 'a8266034799f299c166d0fbf288d714311919f3474cf583044bc5866f6f6b16c'}

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
