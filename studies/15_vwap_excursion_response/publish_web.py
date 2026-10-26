# Presentation-only exporter for 15_vwap_excursion_response. No analytical imports.
SPEC = {'study_id': '15_vwap_excursion_response', 'source_run_id': '20260929T234000Z_a15f', 'publication_id': '15-vwap-excursion-response-20261006-web', 'title': 'VWAP excursion: return and first-touch response', 'summary': 'Fresh two-sigma departures show different return and response behavior by anchor and product. Complete-path denominators and shared-week uncertainty limit these to exploratory price evidence.', 'selection': 'Registered reference', 'reason': 'Explicit registered reference; retain its executed scope and saved qualifications.', 'sources': ['report.md', 'config.json', 'manifest.json', 'inputs.lock.json', 'metrics.json', 'protocol-1.0.0.md'], 'sections': [{'kind': 'text', 'id': 'question', 'title': 'Question and scope', 'body': 'For ES, NQ and GC, what follows the first fresh two-sigma departure from each causal session VWAP, and what follows its first traded contact? The selected concise saved findings contain ten two-minute candles, a twenty-minute horizon, mirrored sides and four overlapping anchors. Longer-horizon evidence remains in the saved full tables.', 'source': 'report.md', 'anchor': 'Question and scope'}, {'kind': 'text', 'id': 'findings', 'title': 'Supported findings', 'body': 'Return probability depends strongly on the anchor population. Continuation-minus-fade endpoint differences are mixed, with several uncertain intervals. First-touch bounce endpoint rates can sit near one half while payoff distributions differ. No optimization or trading edge is inferred from selected rates.', 'source': 'report.md', 'anchor': 'Supported findings'}, {'kind': 'table', 'id': 'departure', 'title': 'Two-sigma departures: eligible twenty-minute outcomes', 'file': 'tables/findings.csv', 'columns': [{'column': {'key': 'session', 'label': 'Anchor'}, 'scale': 1}, {'column': {'key': 'product', 'label': 'product'}, 'scale': 1}, {'column': {'key': 'departure_n', 'label': 'Eligible departures', 'format': 'number', 'precision': 0}, 'scale': 1}, {'column': {'key': 'return_probability', 'label': 'Evolving return', 'format': 'percent', 'precision': 1}, 'scale': 1}, {'column': {'key': 'return_ci_low', 'label': '95% return low', 'format': 'percent', 'precision': 1}, 'scale': 1}, {'column': {'key': 'return_ci_high', 'label': '95% return high', 'format': 'percent', 'precision': 1}, 'scale': 1}, {'column': {'key': 'continuation_delta', 'label': 'Continuation minus fade', 'format': 'number', 'precision': 2, 'unit': 'points'}, 'scale': 1}, {'column': {'key': 'continuation_ci_low', 'label': '95% difference low', 'format': 'number', 'precision': 2, 'unit': 'points'}, 'scale': 1}, {'column': {'key': 'continuation_ci_high', 'label': '95% difference high', 'format': 'number', 'precision': 2, 'unit': 'points'}, 'scale': 1}], 'where': {}, 'description': 'All saved rows'}, {'kind': 'table', 'id': 'touch', 'title': 'First-touch response: separate eligible population', 'file': 'tables/findings.csv', 'columns': [{'column': {'key': 'session', 'label': 'Anchor'}, 'scale': 1}, {'column': {'key': 'product', 'label': 'product'}, 'scale': 1}, {'column': {'key': 'touch_n', 'label': 'Eligible touch responses', 'format': 'number', 'precision': 0}, 'scale': 1}, {'column': {'key': 'bounce_endpoint_probability', 'label': 'Bounce endpoint rate', 'format': 'percent', 'precision': 1}, 'scale': 1}, {'column': {'key': 'bounce_endpoint_ci_low', 'label': '95% low', 'format': 'percent', 'precision': 1}, 'scale': 1}, {'column': {'key': 'bounce_endpoint_ci_high', 'label': '95% high', 'format': 'percent', 'precision': 1}, 'scale': 1}], 'where': {}, 'description': 'All saved rows'}, {'kind': 'text', 'id': 'methods', 'title': 'Definitions and methods', 'body': 'Completed two-minute HLC3 is weighted by bar volume; population sigma is volume weighted. A first fresh strict close beyond two sigma is selected within a causal parent excursion. Entry is the next two-minute open. Primary touch is source one-minute range overlap with the tick-rounded ±one-tick evolving VWAP zone known at minute open; gap or reference overtake alone is not touch. Touch response begins after its containing two-minute candle closes. Upper departure continuation and upper-arrival bounce are long; lower counterparts are short. Continuation delta compares signed continuation with fade endpoint movement in native points. Bounce endpoint probability tests the signed terminal response, not a first-barrier winner or a trading win rate. Unavailable horizons are excluded from eligible outcome denominators. Saved marginal 95% intervals use shared ISO-week cluster draws.', 'source': 'protocol-1.0.0.md', 'anchor': 'Definitions and methods'}, {'kind': 'text', 'id': 'limitations', 'title': 'Limitations and uncertainty', 'body': 'Previously viewed, retrospectively complete history is exploratory: ES/NQ eligible dates begin in 2021 and GC in 2016, ending September 18, 2026. Anchors and thresholds are dependent. Bootstrap zero/all-success cells have unresolved boundary uncertainty, not certainty. Sparse support and exclusions remain in the saved coverage table. No order-flow delta, fills, costs, intraminute barrier order or realized profitability was tested. The optional Pine companion has not been independently compiled in its native environment.', 'source': 'report.md', 'anchor': 'Limitations and uncertainty'}]}
EXPECTED = {'runs/15_vwap_excursion_response/20260929T234000Z_a15f/metrics.json': 'd34d34f581f0289ccf368b72364260325b88e39b869464148885476072cedbab', 'runs/15_vwap_excursion_response/20260929T234000Z_a15f/report.md': '29cb52d9223b58719f341327af60474dcbeda483b67befc5754234608aa3320a', 'runs/15_vwap_excursion_response/20260929T234000Z_a15f/tables/findings.csv': '1c59ad4bd76a418019e7d20ba423ad71982e4353b82dfefde8a2c86280332c6c', 'runs/15_vwap_excursion_response/20260929T234000Z_a15f/config.json': '62d0bb758b89ed50b042106a0abbfe2991a611ee5672c753842492b2d2bc9d9e', 'runs/15_vwap_excursion_response/20260929T234000Z_a15f/manifest.json': 'a7d1a72da155225205ec825e589e2b2335ae3ddd39dab91a29d9c98e5b484218', 'runs/15_vwap_excursion_response/20260929T234000Z_a15f/inputs.lock.json': 'e38008ec8e2b17c21490411cdc4bcfc7f12ecaebaafaaf2440aa47ba080421f8', 'runs/15_vwap_excursion_response/20260929T234000Z_a15f/protocol-1.0.0.md': '231721d996389fb1b259671238b83c61976e727f276dc7c0d60f6aa8bc9294a9'}

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
