# Presentation-only exporter for 01_reversal_follow_through. No analytical imports.
SPEC = {'study_id': '01_reversal_follow_through', 'source_run_id': '20260906T_full_v3', 'publication_id': '01-reversal-follow-through-20261006-web', 'title': 'Reversal follow-through: no clear chart winner', 'summary': 'The retained historical comparison does not establish a clear ES or NQ chart winner. Requested GC 20 evidence is missing; chart identity and timing remain provisional.', 'selection': 'Publication-only choice', 'reason': 'full_v3 retains the expanded chart-selection decision and companion excursion evidence needed for this question. Historical import gaps remain visible; this is a publication choice, not a research reference.', 'sources': ['report.md', 'run_manifest.json', 'import_manifest.json', 'methodology.md', 'data_quality.md'], 'sections': [{'kind': 'text', 'id': 'question', 'title': 'Question and scope', 'body': 'How does reversal follow-through differ across requested ES, NQ and GC Range XV chart sizes? This publication selects the historical full_v3 import because it retains expanded selection and excursion context, not because it is newer. The frozen selected candidates are ES 4 and NQ 10; GC 20 was unavailable.', 'source': 'report.md', 'anchor': 'Question and scope'}, {'kind': 'text', 'id': 'findings', 'title': 'Supported findings', 'body': 'Development leaders and validation-supported choices differ. The test-labelled saved comparison declares no clear winner. Missing GC evidence is retained as missing rather than replaced by available GC 6. The table carries null values and the saved recommendation for that gap.', 'source': 'report.md', 'anchor': 'Supported findings'}, {'kind': 'table', 'id': 'selection', 'title': 'Saved candidate selection and decision', 'file': 'tables/candidate_selection.csv', 'columns': [{'column': {'key': 'asset', 'label': 'asset'}, 'scale': 1}, {'column': {'key': 'development_candidate', 'label': 'development candidate'}, 'scale': 1}, {'column': {'key': 'validation_supported', 'label': 'validation supported'}, 'scale': 1}, {'column': {'key': 'test_clear_winner', 'label': 'test clear winner'}, 'scale': 1}, {'column': {'key': 'recommendation', 'label': 'recommendation'}, 'scale': 1}, {'column': {'key': 'reason', 'label': 'reason'}, 'scale': 1}], 'where': {}, 'description': 'All saved rows'}, {'kind': 'table', 'id': 'test', 'title': 'Selected test-labelled continuation and excursions', 'file': 'tables/cross_asset_summary.csv', 'columns': [{'column': {'key': 'asset', 'label': 'asset'}, 'scale': 1}, {'column': {'key': 'range_setting', 'label': 'Selected setting'}, 'scale': 1}, {'column': {'key': 'test_successes', 'label': 'L≥3 successes', 'format': 'number', 'precision': 0}, 'scale': 1}, {'column': {'key': 'denominator', 'label': 'Eligible reversals', 'format': 'number', 'precision': 0}, 'scale': 1}, {'column': {'key': 'test_probability_L_ge_3', 'label': 'P(L≥3)', 'format': 'percent', 'precision': 1}, 'scale': 1}, {'column': {'key': 'test_ci_low', 'label': '95% low', 'format': 'percent', 'precision': 1}, 'scale': 1}, {'column': {'key': 'test_ci_high', 'label': '95% high', 'format': 'percent', 'precision': 1}, 'scale': 1}, {'column': {'key': 'test_median_MAE_h3_ticks', 'label': 'Three-bar median MAE', 'format': 'number', 'precision': 2, 'unit': 'ticks'}, 'scale': 1}, {'column': {'key': 'test_median_MFE_h3_ticks', 'label': 'Three-bar median MFE', 'format': 'number', 'precision': 2, 'unit': 'ticks'}, 'scale': 1}, {'column': {'key': 'recommendation', 'label': 'recommendation'}, 'scale': 1}], 'where': {}, 'description': 'All saved rows'}, {'kind': 'text', 'id': 'methods', 'title': 'Definitions and methods', 'body': 'A reversal is the first completed non-doji bar opposite the previous run; L counts additional same-direction bars after it. The primary threshold is at least three followers, excluding the reversal. Saved test labels cover August 20–September 4, 2026, after development June 14–August 2 and validation August 4–18 with embargo dates. Selected candidates are frozen before this test-labelled comparison. Saved 95% date-block intervals describe continuation; companion three-bar MAE/MFE is measured from the signal close in product ticks. Excursion extrema are separate, not executable exits.', 'source': 'report.md', 'anchor': 'Definitions and methods'}, {'kind': 'text', 'id': 'limitations', 'title': 'Limitations and uncertainty', 'body': 'This is a historical import not newly revalidated research. Original short-export input files are missing locally. Filename chart labels are provisional Range XV, not verified Range XC; timezone, completion and session semantics are unresolved. Imported test labels do not certify pristine independent confirmation. Missing GC 20 prevents its chart-size comparison. Gross path extrema omit fills, costs and profitability.', 'source': 'report.md', 'anchor': 'Limitations and uncertainty'}]}
EXPECTED = {'runs/01_reversal_follow_through/20260906T_full_v3/import_manifest.json': '0e70ea0d043351aeb3aa00da4080c116aa4ce125206212840bd0f419d2e2d842', 'runs/01_reversal_follow_through/20260906T_full_v3/tables/candidate_selection.csv': 'ea54e4bbf5d255e79ca54552a53b92dbeae717c5911746181dddf7ecea971eb8', 'runs/01_reversal_follow_through/20260906T_full_v3/report.md': '81171d6990d8c44e9dc71cc3d946e641bbf81dabadb2725b238718c0bc1adea9', 'runs/01_reversal_follow_through/20260906T_full_v3/data_quality.md': '60abc607dd14538a988b4fc52a818ab784496dab2501f7546180f24a1d62f558', 'runs/01_reversal_follow_through/20260906T_full_v3/methodology.md': '49cebcf199fbe5371200b17523b29e610a2e9714f8a6f5eb38e7e5582f29a351', 'runs/01_reversal_follow_through/20260906T_full_v3/tables/cross_asset_summary.csv': '73c8d6163dda3c1269303eb2cffca9bbbd5c52bb835a8687f3b07739c3024ed5', 'runs/01_reversal_follow_through/20260906T_full_v3/run_manifest.json': '14cd2c02c36f83fc722a7f9d3d0663e9759dfe8857197e10e3c9aa61bf6a2438'}

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
