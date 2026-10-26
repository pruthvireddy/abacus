# Presentation-only exporter for 11_vwap_conditional_probabilities. No analytical imports.
SPEC = {'study_id': '11_vwap_conditional_probabilities', 'source_run_id': '20260924T155331Z_vwap11', 'publication_id': '11-vwap-conditional-probabilities-20261006-web', 'title': 'VWAP checkpoints: return, extension and destination probabilities', 'summary': 'Conditional checkpoint and destination probabilities describe mature VWAP episodes. Geometry adds only small context-model improvements; these are exploratory associations, not trading probabilities.', 'selection': 'Registered reference', 'reason': 'Explicit registered reference; retain its executed scope and saved qualifications.', 'sources': ['report.md', 'config.json', 'manifest.json', 'inputs.lock.json', 'metrics.json', 'protocol-1.0.0.md'], 'sections': [{'kind': 'text', 'id': 'question', 'title': 'Question and scope', 'body': 'The saved run asks A: whether a mature departure returns to checkpoint-frozen VWAP within thirty minutes; B: whether frozen VWAP return occurs before a half-sigma extension; C: which of frozen day and session VWAP is reached first after a session failure. ES, NQ and GC remain separate.', 'source': 'report.md', 'anchor': 'Question and scope'}, {'kind': 'text', 'id': 'findings', 'title': 'Supported findings', 'body': 'Checkpoint rates depend on the selected population. Return-first and extension-first compete with neither and same-bar ambiguous outcomes. Destination events retain both day-first and session-first outcomes. Added geometry improves context prediction only modestly and without an executable strategy claim.', 'source': 'report.md', 'anchor': 'Supported findings'}, {'kind': 'table', 'id': 'atlas', 'title': 'Primary all-history probabilities by product', 'file': 'tables/probability_atlas.csv', 'columns': [{'column': {'key': 'question', 'label': 'question'}, 'scale': 1}, {'column': {'key': 'product', 'label': 'product'}, 'scale': 1}, {'column': {'key': 'population', 'label': 'population'}, 'scale': 1}, {'column': {'key': 'future_event', 'label': 'Event'}, 'scale': 1}, {'column': {'key': 'numerator', 'label': 'numerator', 'format': 'number', 'precision': 0}, 'scale': 1}, {'column': {'key': 'denominator', 'label': 'denominator', 'format': 'number', 'precision': 0}, 'scale': 1}, {'column': {'key': 'probability', 'label': 'probability', 'format': 'percent', 'precision': 1}, 'scale': 1}, {'column': {'key': 'ci_low', 'label': '95% low', 'format': 'percent', 'precision': 1}, 'scale': 1}, {'column': {'key': 'ci_high', 'label': '95% high', 'format': 'percent', 'precision': 1}, 'scale': 1}, {'column': {'key': 'episodes', 'label': 'episodes', 'format': 'number', 'precision': 0}, 'scale': 1}], 'where': {}, 'description': 'All saved rows'}, {'kind': 'table', 'id': 'competition', 'title': 'B: return versus extension, including unresolved outcomes', 'file': 'tables/question_b_outcomes.csv', 'columns': [{'column': {'key': 'product', 'label': 'product'}, 'scale': 1}, {'column': {'key': 'outcome_class', 'label': 'Outcome'}, 'scale': 1}, {'column': {'key': 'numerator', 'label': 'numerator', 'format': 'number', 'precision': 0}, 'scale': 1}, {'column': {'key': 'denominator', 'label': 'denominator', 'format': 'number', 'precision': 0}, 'scale': 1}, {'column': {'key': 'probability', 'label': 'probability', 'format': 'percent', 'precision': 1}, 'scale': 1}, {'column': {'key': 'ci_low', 'label': '95% low', 'format': 'percent', 'precision': 1}, 'scale': 1}, {'column': {'key': 'ci_high', 'label': '95% high', 'format': 'percent', 'precision': 1}, 'scale': 1}], 'where': {'split': ['all'], 'anchor': ['ALL'], 'facet': ['overall'], 'product': ['ES', 'NQ', 'GC']}, 'description': 'All-history overall product outcomes across anchors'}, {'kind': 'table', 'id': 'destinations', 'title': 'C: day versus session destination', 'file': 'tables/question_c_outcomes.csv', 'columns': [{'column': {'key': 'product', 'label': 'product'}, 'scale': 1}, {'column': {'key': 'outcome_class', 'label': 'Outcome'}, 'scale': 1}, {'column': {'key': 'numerator', 'label': 'numerator', 'format': 'number', 'precision': 0}, 'scale': 1}, {'column': {'key': 'denominator', 'label': 'denominator', 'format': 'number', 'precision': 0}, 'scale': 1}, {'column': {'key': 'probability', 'label': 'probability', 'format': 'percent', 'precision': 1}, 'scale': 1}, {'column': {'key': 'ci_low', 'label': '95% low', 'format': 'percent', 'precision': 1}, 'scale': 1}, {'column': {'key': 'ci_high', 'label': '95% high', 'format': 'percent', 'precision': 1}, 'scale': 1}], 'where': {'split': ['all'], 'anchor': ['ALL'], 'facet': ['overall'], 'product': ['ES', 'NQ', 'GC']}, 'description': 'All-history overall product destination outcomes'}, {'kind': 'table', 'id': 'models', 'title': 'Later evaluation: context versus added geometry', 'file': 'tables/model_scores.csv', 'columns': [{'column': {'key': 'question', 'label': 'question'}, 'scale': 1}, {'column': {'key': 'product', 'label': 'product'}, 'scale': 1}, {'column': {'key': 'rows', 'label': 'Evaluated rows', 'format': 'number', 'precision': 0}, 'scale': 1}, {'column': {'key': 'specific_augmented_coverage', 'label': 'Specific-cell coverage', 'format': 'percent', 'precision': 1}, 'scale': 1}, {'column': {'key': 'baseline_brier', 'label': 'Baseline Brier', 'format': 'number', 'precision': 4}, 'scale': 1}, {'column': {'key': 'augmented_brier', 'label': 'Augmented Brier', 'format': 'number', 'precision': 4}, 'scale': 1}, {'column': {'key': 'brier_difference', 'label': 'Difference', 'format': 'number', 'precision': 4}, 'scale': 1}, {'column': {'key': 'difference_ci_low', 'label': '95% difference low', 'format': 'number', 'precision': 4}, 'scale': 1}, {'column': {'key': 'difference_ci_high', 'label': '95% difference high', 'format': 'number', 'precision': 4}, 'scale': 1}, {'column': {'key': 'relative_error_reduction', 'label': 'Relative Brier change', 'format': 'percent', 'precision': 1}, 'scale': 1}], 'where': {'split': ['evaluation'], 'product': ['ES', 'NQ', 'GC']}, 'description': 'Combined validation/final evaluation; development-only model fit'}, {'kind': 'text', 'id': 'methods', 'title': 'Definitions and methods', 'body': 'Fresh departure closes at least max(one sigma, four ticks) from VWAP. Episodes mature after thirty minutes; checkpoint clock minute is divisible by ten and a full thirty-minute path must remain. A contact is future range intersection with checkpoint-frozen VWAP ±one tick; checkpoints already inside the zone are null. B freezes both barriers at the checkpoint and their unequal distances make fifty percent an inappropriate baseline. C requires a qualifying session-VWAP failure between mature day/session destinations, separated by at least eight ticks and a quarter day sigma, with thirty-minute lockout. Table outcomes use eligible checkpoint/event denominators, not independent trades. Saved 95% intervals use shared ISO-week clusters. Context-only models use frozen development cells and support fallbacks; negative relative Brier change means lower prediction error.', 'source': 'protocol-1.0.0.md', 'anchor': 'Definitions and methods'}, {'kind': 'text', 'id': 'limitations', 'title': 'Limitations and uncertainty', 'body': 'Previously viewed all-history evidence is exploratory. Episodes, repeated checkpoints and two-/five-minute sensitivities are dependent. OHLC cannot order two destinations touched in one candle; ambiguous is retained. Conditional probabilities and small model improvements do not prove causality, fills, net profitability or a pristine holdout.', 'source': 'report.md', 'anchor': 'Limitations and uncertainty'}]}
EXPECTED = {'runs/11_vwap_conditional_probabilities/20260924T155331Z_vwap11/tables/question_b_outcomes.csv': 'fbb4bb07ce76b056c31cf328a5694656f2dd23a41aecd63f03b3258058261266', 'runs/11_vwap_conditional_probabilities/20260924T155331Z_vwap11/config.json': 'bc20fc9737c239b4cdaa69f0e667666bd10d48831f2a3264b6bd868f46e03465', 'runs/11_vwap_conditional_probabilities/20260924T155331Z_vwap11/tables/question_c_outcomes.csv': 'b7473b7ccc56a2464a018594de0d65c798749991db238d5bd1c20d9b15613708', 'runs/11_vwap_conditional_probabilities/20260924T155331Z_vwap11/metrics.json': 'd4409323a7247d8c7d43811701fde7c0c2941af066f17edffd5abc6548933dd1', 'runs/11_vwap_conditional_probabilities/20260924T155331Z_vwap11/manifest.json': 'cafc18cc07544be5a99dcfd7080b2aa4db8d8b160de1b9125ffe0ef79bce5ae7', 'runs/11_vwap_conditional_probabilities/20260924T155331Z_vwap11/tables/model_scores.csv': '340fe869a4495c9436d329f79fa53cd4fecd0973f082f0fc410944e20b0293cc', 'runs/11_vwap_conditional_probabilities/20260924T155331Z_vwap11/inputs.lock.json': '22cef60ac3a493363db04a2d1507476a22e9dbc9c068307a63308106469c6faf', 'runs/11_vwap_conditional_probabilities/20260924T155331Z_vwap11/tables/probability_atlas.csv': 'be1de667e067371c42e64c380ef981992ab954cb3073d3dd3ce051b5efdedbc1', 'runs/11_vwap_conditional_probabilities/20260924T155331Z_vwap11/protocol-1.0.0.md': 'e39f2ff362ab27338d7b0cf1a4ee1630f64c63e76afd9d0839dc01f3489188de', 'runs/11_vwap_conditional_probabilities/20260924T155331Z_vwap11/report.md': '864e994c01736fb6e8044b8c72f2ab9226a0645f71c0ecf113a5d3026d5a0843'}

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
