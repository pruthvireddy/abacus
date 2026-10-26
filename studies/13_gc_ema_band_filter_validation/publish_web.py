# Presentation-only exporter for 13_gc_ema_band_filter_validation. No analytical imports.
SPEC = {'study_id': '13_gc_ema_band_filter_validation', 'source_run_id': '20260926T000219Z_gc_band_filters_v1', 'publication_id': '13-gc-ema-band-filter-validation-20261006-web', 'title': 'GC lower band: filter improvement remains uncertain', 'summary': 'An upper-half signal close was selected in 2025. Its chronological 2026 improvement remains uncertain, and the filtered score is negative; this is conditional path evidence.', 'selection': 'Registered reference', 'reason': 'Explicit registered reference; retain its executed scope and saved qualifications.', 'sources': ['report.md', 'config.json', 'manifest.json', 'inputs.lock.json', 'metrics.json'], 'sections': [{'kind': 'text', 'id': 'question', 'title': 'Question and scope', 'body': 'Can a simple signal-time filter improve GC outer-lower EMA band long excursions? The saved comparison covers 2025 and 2026 YTD, next complete five-minute unadjusted open, ten-bar cooldown and twenty-bar future horizon.', 'source': 'report.md', 'anchor': 'Question and scope'}, {'kind': 'text', 'id': 'findings', 'title': 'Supported findings', 'body': 'The frozen selection chose upper-half close. The chronological check improved directionally, but its difference interval spans zero and its score remains negative. All nine filters and the unfiltered baseline are retained below, rather than selecting only favorable rows.', 'source': 'report.md', 'anchor': 'Supported findings'}, {'kind': 'table', 'id': 'candidate-grid', 'title': 'All filters and baseline by year', 'file': 'tables/primary.csv', 'columns': [{'column': {'key': 'rule', 'label': 'rule'}, 'scale': 1}, {'column': {'key': 'year', 'label': 'year', 'format': 'number', 'precision': 0}, 'scale': 1}, {'column': {'key': 'accepted_signals', 'label': 'Accepted signals', 'format': 'number', 'precision': 0}, 'scale': 1}, {'column': {'key': 'valid_n', 'label': 'Valid paths', 'format': 'number', 'precision': 0}, 'scale': 1}, {'column': {'key': 'excluded', 'label': 'excluded', 'format': 'number', 'precision': 0}, 'scale': 1}, {'column': {'key': 'mean_mae_sigma', 'label': 'Mean MAE', 'format': 'number', 'precision': 2, 'unit': 'sigma'}, 'scale': 1}, {'column': {'key': 'mean_mfe_sigma', 'label': 'Mean MFE', 'format': 'number', 'precision': 2, 'unit': 'sigma'}, 'scale': 1}, {'column': {'key': 'mean_clipped_score', 'label': 'Capped score', 'format': 'number', 'precision': 2, 'unit': 'sigma'}, 'scale': 1}, {'column': {'key': 'score_delta_vs_unfiltered', 'label': 'Difference vs baseline', 'format': 'number', 'precision': 2, 'unit': 'sigma'}, 'scale': 1}, {'column': {'key': 'score_delta_ci_low', 'label': '95% difference low', 'format': 'number', 'precision': 2, 'unit': 'sigma'}, 'scale': 1}, {'column': {'key': 'score_delta_ci_high', 'label': '95% difference high', 'format': 'number', 'precision': 2, 'unit': 'sigma'}, 'scale': 1}], 'where': {}, 'description': 'All saved rows'}, {'kind': 'text', 'id': 'methods', 'title': 'Definitions and methods', 'body': 'A signal closes at or below EMA225 minus three population residual standard deviations. Upper-half close requires (close − low)/(high − low) at least one half. Cooldown is reapplied after each filter. Score is mean clipped MFE/sigma minus clipped MAE/sigma, each capped at ten. Development selects under frozen support, lower-MAE and MFE-retention criteria; the selected rule is applied unchanged in the later year. Saved approximate 95% ISO-week bootstrap intervals are pointwise, uncorrected for the candidate search.', 'source': 'report.md', 'anchor': 'Definitions and methods'}, {'kind': 'text', 'id': 'limitations', 'title': 'Limitations and uncertainty', 'body': '2026 YTD had already been viewed in Study 12 and is not a pristine holdout. Sensitivity cells are correlated. Adjusted chart history is retrospective; five-minute OHLC cannot resolve target/stop ordering. Scores and excursion extrema do not model costs, executable exits or profitability.', 'source': 'report.md', 'anchor': 'Limitations and uncertainty'}]}
EXPECTED = {'runs/13_gc_ema_band_filter_validation/20260926T000219Z_gc_band_filters_v1/manifest.json': '05f818e710e819549df43732c46a97e778f06407f6f6bb9ac978f5078cfd722a', 'runs/13_gc_ema_band_filter_validation/20260926T000219Z_gc_band_filters_v1/tables/primary.csv': '86c72f35167727daac4e4709ff9d6231d1d19eec776196c52f3de23c1f88982d', 'runs/13_gc_ema_band_filter_validation/20260926T000219Z_gc_band_filters_v1/report.md': 'ce3afc67d178b306262b5e43cad39af30c2b9e9ec90e9a0b5ca56f0ec3e4078b', 'runs/13_gc_ema_band_filter_validation/20260926T000219Z_gc_band_filters_v1/metrics.json': '215dd15c5f6f9f9c0f05ab7283d7add40d5a275e735352d2fba7b7c0d91ddaed', 'runs/13_gc_ema_band_filter_validation/20260926T000219Z_gc_band_filters_v1/inputs.lock.json': 'f398f6e25f6958cb6d25102276db5329fabd9ec16f4214374feb3b901f2896c7', 'runs/13_gc_ema_band_filter_validation/20260926T000219Z_gc_band_filters_v1/config.json': '82da33fb3a1f5e03711d2f8633e541cf0ae56c234be88b7a79e2207185c1a936'}

import argparse,csv,hashlib,json,math,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def transfer(raw,column,scale):
 if raw=='':return None
 if column.get('format'):
  value=float(raw)*scale
  if not math.isfinite(value):
   raise ValueError(f"Non-finite value for column {column['key']}: {raw!r} at scale {scale!r}")
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
   if not chosen or len(chosen)>100:
    raise ValueError(f"Section {item['id']} from {item['file']} selects {len(chosen)} rows; expected 1 through 100")
   output=[]
   for source_row,row in chosen:
    target={}
    for field in item['columns']:
     c=field['column'];k=c['key']
     try:target[k]=transfer(row[k],c,field['scale'])
     except ValueError as error:
      raise ValueError(f"Section {item['id']} from {item['file']}, column {k}: {error}") from error
     bindings.append({'section':item['id'],'output_row':len(output),'column':k,'source':str((run/item['file']).relative_to(ROOT)),'data_row_1_based':source_row,'source_column':k,'source_raw':row[k],'scale':field['scale'],'value':target[k]})
    output.append(target)
   sections.append({'kind':'table','id':item['id'],'title':item['title'],'columns':[f['column'] for f in item['columns']],'rows':output})
 provenance=f"Study {SPEC['study_id']}; source run {SPEC['source_run_id']}. {SPEC['selection']}: {SPEC['reason']}\n\nPresentation revision {revision}, web-study-report-1.0. Saved numerical tables are the authority; only selected rows and columns are presented. No new statistics or research execution. The publication record identifies this JSON and its selected assets."
 sections.append({'kind':'text','id':'sources-provenance','title':'Source and presentation provenance','body':provenance})
 pub={'schemaVersion':'1.0','id':SPEC['publication_id'],'title':SPEC['title'],'summary':SPEC['summary'],'publishedAt':'2026-10-06T23:09:36Z','source':{'producer':'sahadeva','runId':SPEC['source_run_id']},'sections':sections}
 artifacts=[]
 for name in sorted(sources):
  p=run/name;relative=str(p.relative_to(ROOT))
  if digest(p)!=EXPECTED[relative]:
   raise ValueError(f"Source artifact hash mismatch: {relative}")
  artifacts.append({'path':relative,'sha256':digest(p)})
 return pub,{'study_id':SPEC['study_id'],'source_run_id':SPEC['source_run_id'],'revision_id':revision,'sources':artifacts,'bindings':bindings,'claims':claims,'table_selections':[{'section':i['id'],'source':i['file'],'where':i['where'],'description':i['description']} for i in SPEC['sections'] if i['kind']=='table'],'figures':[]}

def main(argv=None):
 parser=argparse.ArgumentParser(description='Presentation only: select pinned saved evidence; never execute research.')
 parser.add_argument('--revision',required=True);parser.add_argument('--check',action='store_true');args=parser.parse_args(argv)
 if not __import__('re').fullmatch(r'[A-Za-z0-9_-]+',args.revision):
  raise ValueError(f"Unsafe revision identifier: {args.revision!r}")
 out=ROOT/'reports/exports'/SPEC['study_id']/SPEC['source_run_id']/args.revision
 pub,mapping=prepare(args.revision)
 if args.check:
  if json.loads((out/'publication.json').read_text())!=pub:
   raise ValueError(f"Publication does not match prepared saved evidence: {out/'publication.json'}")
  if json.loads((out/'source-map.json').read_text())!=mapping:
   raise ValueError(f"Source map does not match prepared saved evidence: {out/'source-map.json'}")
  print(f"{SPEC['study_id']}: {len(mapping['bindings'])} saved-cell transfers and source hashes match.")
 else:
  out.mkdir(parents=True,exist_ok=False)
  for name,value in [('publication.json',pub),('source-map.json',mapping)]:
   (out/name).write_text(json.dumps(value,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
  (out/'provenance').mkdir();shutil.copyfile(__file__,out/'provenance/publish_web.py')
  (out/'README.md').write_text(f"# {SPEC['title']}\n\n[Publication](publication.json) · [Source map](source-map.json) · [Manifest](manifest.json) · [Verification](verification.json)\n\n{SPEC['selection']}: {SPEC['reason']}\n\nBounded table-first presentation. Full tables and research figures remain in the saved run. No new calculations. Reproduce into a fresh revision and use a fresh publication ID for changed content.\n")
  print(out.relative_to(ROOT))

if __name__=='__main__':
 main()
