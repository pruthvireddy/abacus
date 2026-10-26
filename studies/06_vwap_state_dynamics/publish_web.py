# Presentation-only exporter for 06_vwap_state_dynamics. No analytical imports.
SPEC = {'study_id': '06_vwap_state_dynamics', 'source_run_id': '20260923T180000Z_state06c', 'publication_id': '06-vwap-state-dynamics-20261006-web', 'title': 'VWAP states: persistence, slope conflict and fair-price error', 'summary': 'Persistent states retain more future residence, while opposing slopes predict more crossing. Coarse matching shrinks both gaps; local-anchor checks reverse the pooled VWAP–TWAP conclusion.', 'selection': 'Registered reference', 'reason': 'Explicit registered reference; retain its executed scope and saved qualifications.', 'sources': ['report.md', 'config.json', 'manifest.json', 'inputs.lock.json', 'metrics.json', 'protocol-1.0.0.md'], 'sections': [{'kind': 'text', 'id': 'question', 'title': 'Question and scope', 'body': 'Three descriptive questions use ES, NQ and GC two-minute bars: whether persistent versus rotational VWAP states retain the next thirty-minute residence; whether opposing price/VWAP slopes predict crossing; and whether frozen VWAP or TWAP better locates the median of future thirty-minute one-minute closes. The atlas pools products only as specified in the saved run; errors below keep products separate.', 'source': 'report.md', 'anchor': 'Question and scope'}, {'kind': 'text', 'id': 'findings', 'title': 'Supported findings', 'body': 'The raw state and slope gaps shrink after matching shared context. The pooled primary fair-price comparison favors VWAP, but Asia and New York local-anchor checks favor TWAP. Last-known price has smaller absolute error than either reference. Barrier follow-ups do not establish a trading rule.', 'source': 'report.md', 'anchor': 'Supported findings'}, {'kind': 'table', 'id': 'atlas', 'title': 'All-history primary probability atlas', 'file': 'tables/probability_atlas.csv', 'columns': [{'column': {'key': 'question', 'label': 'question'}, 'scale': 1}, {'column': {'key': 'condition', 'label': 'condition'}, 'scale': 1}, {'column': {'key': 'landmarks', 'label': 'landmarks', 'format': 'number', 'precision': 0}, 'scale': 1}, {'column': {'key': 'outcome_missing', 'label': 'Missing outcome', 'format': 'number', 'precision': 0}, 'scale': 1}, {'column': {'key': 'numerator', 'label': 'numerator', 'format': 'number', 'precision': 0}, 'scale': 1}, {'column': {'key': 'denominator', 'label': 'denominator', 'format': 'number', 'precision': 0}, 'scale': 1}, {'column': {'key': 'probability', 'label': 'Probability', 'format': 'percent', 'precision': 1}, 'scale': 1}, {'column': {'key': 'ci_low', 'label': '95% low', 'format': 'percent', 'precision': 1}, 'scale': 1}, {'column': {'key': 'ci_high', 'label': '95% high', 'format': 'percent', 'precision': 1}, 'scale': 1}, {'column': {'key': 'baseline', 'label': 'baseline'}, 'scale': 1}], 'where': {}, 'description': 'All saved rows'}, {'kind': 'table', 'id': 'matched', 'title': 'State and slope differences: raw versus matched', 'file': 'tables/matched_comparisons.csv', 'columns': [{'column': {'key': 'question', 'label': 'question'}, 'scale': 1}, {'column': {'key': 'condition', 'label': 'condition'}, 'scale': 1}, {'column': {'key': 'baseline', 'label': 'baseline'}, 'scale': 1}, {'column': {'key': 'treated_n', 'label': 'Raw candidate n', 'format': 'number', 'precision': 0}, 'scale': 1}, {'column': {'key': 'baseline_n', 'label': 'Raw baseline n', 'format': 'number', 'precision': 0}, 'scale': 1}, {'column': {'key': 'matched_treated', 'label': 'Matched candidate n', 'format': 'number', 'precision': 0}, 'scale': 1}, {'column': {'key': 'matched_baseline', 'label': 'Matched baseline n', 'format': 'number', 'precision': 0}, 'scale': 1}, {'column': {'key': 'raw_difference', 'label': 'Raw difference', 'format': 'number', 'precision': 1, 'unit': 'pp'}, 'scale': 100}, {'column': {'key': 'matched_difference', 'label': 'Matched difference', 'format': 'number', 'precision': 1, 'unit': 'pp'}, 'scale': 100}, {'column': {'key': 'matched_ci_low', 'label': '95% matched low', 'format': 'number', 'precision': 1, 'unit': 'pp'}, 'scale': 100}, {'column': {'key': 'matched_ci_high', 'label': '95% matched high', 'format': 'number', 'precision': 1, 'unit': 'pp'}, 'scale': 100}], 'where': {'product': ['ALL'], 'split': ['all']}, 'description': 'Two pooled primary contrasts, raw and matched cohorts retained'}, {'kind': 'table', 'id': 'errors', 'title': 'Fair-price error by product', 'file': 'tables/paired_errors.csv', 'columns': [{'column': {'key': 'product', 'label': 'product'}, 'scale': 1}, {'column': {'key': 'denominator', 'label': 'Eligible pairs', 'format': 'number', 'precision': 0}, 'scale': 1}, {'column': {'key': 'vwap_mae', 'label': 'VWAP mean absolute error', 'format': 'number', 'precision': 2, 'unit': 'points'}, 'scale': 1}, {'column': {'key': 'twap_mae', 'label': 'TWAP mean absolute error', 'format': 'number', 'precision': 2, 'unit': 'points'}, 'scale': 1}, {'column': {'key': 'last_price_mae', 'label': 'Last-price mean absolute error', 'format': 'number', 'precision': 2, 'unit': 'points'}, 'scale': 1}, {'column': {'key': 'mean_error_difference', 'label': 'VWAP minus TWAP', 'format': 'number', 'precision': 2, 'unit': 'points'}, 'scale': 1}, {'column': {'key': 'mean_error_ci_low', 'label': '95% difference low', 'format': 'number', 'precision': 2, 'unit': 'points'}, 'scale': 1}, {'column': {'key': 'mean_error_ci_high', 'label': '95% difference high', 'format': 'number', 'precision': 2, 'unit': 'points'}, 'scale': 1}], 'where': {'split': ['all'], 'product': ['ES', 'NQ', 'GC']}, 'description': 'All-history product-specific primary fair-price errors'}, {'kind': 'text', 'id': 'methods', 'title': 'Definitions and methods', 'body': 'Persistent means at least twelve of fifteen closes on one side and at most one cross; rotational means six to nine above with at least three crosses. Future residence uses evolving causal VWAP. Prior thirty-minute price and VWAP slopes use the frozen ATR-scaled cutpoints. Matching uses coarse shared context strata and leaves unmatched observations explicit. Fair-price errors compare frozen current references against the same future median close; ties and missing outcomes remain separate. Saved probability and difference intervals are shared-date cluster 95%, unadjusted for the three-question family; paired error is in native product points.', 'source': 'protocol-1.0.0.md', 'anchor': 'Definitions and methods'}, {'kind': 'text', 'id': 'limitations', 'title': 'Limitations and uncertainty', 'body': 'All history is exploratory and outcomes had been viewed before the protocol. Landmarks and products are correlated; matching is not a causal adjustment. Primary Globex and local-anchor replications disagree, so their estimates cannot be pooled into a universal reference preference. No fill, spread, cost, execution or profitability result follows from residence or prediction accuracy.', 'source': 'report.md', 'anchor': 'Limitations and uncertainty'}]}
EXPECTED = {'runs/06_vwap_state_dynamics/20260923T180000Z_state06c/tables/matched_comparisons.csv': '0728cbc150ddc96cac9790f2737f5d13991759002a9406c267a68cf51b074bf5', 'runs/06_vwap_state_dynamics/20260923T180000Z_state06c/config.json': '20bfd9a96c34e07461f82ac162516f9b2186b5ce7e32d4fa100e7e7070677333', 'runs/06_vwap_state_dynamics/20260923T180000Z_state06c/tables/paired_errors.csv': '6493a5cc88efe112e03cec07844722fccd246d07c379b7e08570c62da6fac701', 'runs/06_vwap_state_dynamics/20260923T180000Z_state06c/metrics.json': '9f55001ff438e373d473e7255164c8605e7f1f06f8354a06eba48067af80176c', 'runs/06_vwap_state_dynamics/20260923T180000Z_state06c/manifest.json': 'd4be745fb40fb57e0bf24e332a1474844e7882e34e7e8f0edecb76eacca25d0b', 'runs/06_vwap_state_dynamics/20260923T180000Z_state06c/inputs.lock.json': '6e25f9e2e0ea89bd5771cac08f545ea135b6b12956c9eb01de8ae4b562490401', 'runs/06_vwap_state_dynamics/20260923T180000Z_state06c/tables/probability_atlas.csv': '59b65a5052824d598d7102e763df215ceec44f412c6eac7add85c05ed620c51d', 'runs/06_vwap_state_dynamics/20260923T180000Z_state06c/protocol-1.0.0.md': '968752702849d1e2f0aed257948f24659c45e0a56dc464bf10555b9ecc38b2f1', 'runs/06_vwap_state_dynamics/20260923T180000Z_state06c/report.md': '27ae33240a2de3e3e859b214a1903e2842039aff9d860ff69e774c36040d278a'}

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
