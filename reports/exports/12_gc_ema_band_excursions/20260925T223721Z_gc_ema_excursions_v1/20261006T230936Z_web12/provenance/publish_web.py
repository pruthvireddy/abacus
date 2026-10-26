# Presentation-only exporter for 12_gc_ema_band_excursions. No analytical imports.
SPEC = {'study_id': '12_gc_ema_band_excursions', 'source_run_id': '20260925T223721Z_gc_ema_excursions_v1', 'publication_id': '12-gc-ema-band-excursions-20261006-web', 'title': 'GC outer lower band: yearly excursion paths', 'summary': 'Next-open GC excursions after a close below the outer lower EMA band vary by year. The saved default grid is descriptive; excursion extrema are not executable exits.', 'selection': 'Registered reference', 'reason': 'Explicit registered reference; retain its executed scope and saved qualifications.', 'sources': ['report.md', 'config.json', 'manifest.json', 'inputs.lock.json', 'metrics.json'], 'sections': [{'kind': 'text', 'id': 'question', 'title': 'Question and scope', 'body': 'After a five-minute GC close at or below EMA225 minus three residual standard deviations, how much adverse and favorable excursion occurs from the next complete unadjusted open? The default saved comparison uses ten-bar cooldown and twenty future five-minute bars, a hundred-minute horizon.', 'source': 'report.md', 'anchor': 'Question and scope'}, {'kind': 'text', 'id': 'findings', 'title': 'Supported findings', 'body': 'The saved yearly table reports both adverse and favorable path extrema rather than choosing an MFE exit. Coverage, valid denominators and uncertainty differ by year. The larger cooldown/horizon grid is a correlated sensitivity, not independent replication or optimized trading evidence.', 'source': 'report.md', 'anchor': 'Supported findings'}, {'kind': 'table', 'id': 'yearly', 'title': 'Default grid: yearly valid paths and excursion means', 'file': 'tables/yearly.csv', 'columns': [{'column': {'key': 'year', 'label': 'year', 'format': 'number', 'precision': 0}, 'scale': 1}, {'column': {'key': 'accepted_signals', 'label': 'Accepted signals', 'format': 'number', 'precision': 0}, 'scale': 1}, {'column': {'key': 'valid_n', 'label': 'Valid paths', 'format': 'number', 'precision': 0}, 'scale': 1}, {'column': {'key': 'mean_mae', 'label': 'Mean MAE', 'format': 'number', 'precision': 2, 'unit': 'points'}, 'scale': 1}, {'column': {'key': 'mean_mae_ci_low', 'label': '95% MAE low', 'format': 'number', 'precision': 2, 'unit': 'points'}, 'scale': 1}, {'column': {'key': 'mean_mae_ci_high', 'label': '95% MAE high', 'format': 'number', 'precision': 2, 'unit': 'points'}, 'scale': 1}, {'column': {'key': 'mean_mfe', 'label': 'Mean MFE', 'format': 'number', 'precision': 2, 'unit': 'points'}, 'scale': 1}, {'column': {'key': 'mean_mfe_ci_low', 'label': '95% MFE low', 'format': 'number', 'precision': 2, 'unit': 'points'}, 'scale': 1}, {'column': {'key': 'mean_mfe_ci_high', 'label': '95% MFE high', 'format': 'number', 'precision': 2, 'unit': 'points'}, 'scale': 1}], 'where': {'cooldown': ['10'], 'horizon': ['20']}, 'description': 'All saved years at the declared default cooldown/horizon; no new aggregation'}, {'kind': 'text', 'id': 'methods', 'title': 'Definitions and methods', 'body': 'EMA uses adjusted five-minute closes; sigma is population standard deviation of rolling close-minus-EMA residuals, with pinned readiness and feature availability. Outcomes use raw contract coordinates from the next full five-minute open. MAE and MFE are nonnegative extrema over the whole eligible future path and need not occur in an executable order. Saved approximate 95% ISO-week bootstrap bounds accompany yearly means. Accepted signals include later excluded paths; valid n is the outcome denominator. The twenty-bar horizon must be contiguous, complete and retain contract/adjustment identity.', 'source': 'report.md', 'anchor': 'Definitions and methods'}, {'kind': 'text', 'id': 'limitations', 'title': 'Limitations and uncertainty', 'body': 'Coverage begins partway through 2010 and 2026 is YTD through September 18. Whole-day and adjusted continuous history eligibility is retrospective rather than point-in-time. Missing minutes, partial bars, gaps and roll/adjustment changes exclude paths. No stops, fees, fills, slippage or net profitability were tested; the saved interactive report is not imported into the public page.', 'source': 'report.md', 'anchor': 'Limitations and uncertainty'}]}
EXPECTED = {'runs/12_gc_ema_band_excursions/20260925T223721Z_gc_ema_excursions_v1/report.md': '46896e6e20ced611a743d4ff0bdc91da0ab3023327da54c56af689de601991e3', 'runs/12_gc_ema_band_excursions/20260925T223721Z_gc_ema_excursions_v1/manifest.json': 'fa3c10ae5f931b7b793d1f1a9efc684ca5c6c4135090a3c0a1fe09c29a2999f3', 'runs/12_gc_ema_band_excursions/20260925T223721Z_gc_ema_excursions_v1/inputs.lock.json': 'af1c6039073e52dffed9cb35cdd007ed3fc097e41762939e9a803d7dd08c8d87', 'runs/12_gc_ema_band_excursions/20260925T223721Z_gc_ema_excursions_v1/config.json': 'b66a43bc5340842f20d2af6a27c9f722e8a1e077bf6064b76c8300ecef9b180d', 'runs/12_gc_ema_band_excursions/20260925T223721Z_gc_ema_excursions_v1/metrics.json': '73e07a890898ae38825c0f38ea10ba92894cc520c8299a5492ddf19ba1829b9e', 'runs/12_gc_ema_band_excursions/20260925T223721Z_gc_ema_excursions_v1/tables/yearly.csv': '20993a93b12a82944ecbad0cfaf78bd3bda9b181be9edfc12e743dc1cc3715b9'}

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
