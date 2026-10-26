# Presentation-only exporter for 10_range_xv_session_overlay. No analytical imports.
SPEC = {'study_id': '10_range_xv_session_overlay', 'source_run_id': '20260924T145715Z_session_v1', 'publication_id': '10-range-xv-session-overlay-20261006-web-r2', 'title': 'Session overlay: local colour patterns do not prove edge', 'summary': 'Asia, London and New York overlays preserve negative price screens. Selected NQ colour contrasts vary by session, while the confirmation wait policy remains negative.', 'selection': 'Registered reference', 'reason': 'Explicit registered reference; retain its executed scope and saved qualifications.', 'sources': ['report.md', 'config.json', 'manifest.json', 'inputs.lock.json', 'metrics.json', 'source-snapshot/plan.md'], 'sections': [{'kind': 'text', 'id': 'question', 'title': 'Question and scope', 'body': 'This separate overlay run segments the saved Study 07 candidate, Study 08 countertrend and corrected Study 09 confirmation cohorts. It does not combine their observations into a new sample. Candidate tables show all products; colour tables use the explicitly selected NQ 10 illustration.', 'source': 'report.md', 'anchor': 'Question and scope'}, {'kind': 'text', 'id': 'findings', 'title': 'Supported findings', 'body': 'No Study 07 idea/product/session passes the declared price screen. Some Study 08 NQ 10 cells beat their other two named segments only narrowly; Study 09 confirmation shows some ordinary-control lifts but far less segment-specific evidence. The saved wait means remain negative in every screened chart/direction/session cell. Colour differences and price payoffs disagree.', 'source': 'report.md', 'anchor': 'Supported findings'}, {'kind': 'table', 'id': 'candidate-overlay', 'title': 'Candidate means by product and primary segment', 'file': 'tables/07_summary.csv', 'columns': [{'column': {'key': 'product', 'label': 'product'}, 'scale': 1}, {'column': {'key': 'idea', 'label': 'idea'}, 'scale': 1}, {'column': {'key': 'segment', 'label': 'segment'}, 'scale': 1}, {'column': {'key': 'denominator', 'label': 'Original opportunities', 'format': 'number', 'precision': 0}, 'scale': 1}, {'column': {'key': 'candidate_trades', 'label': 'Executed proxy trades', 'format': 'number', 'precision': 0}, 'scale': 1}, {'column': {'key': 'estimate', 'label': 'Mean after haircut', 'format': 'number', 'precision': 2, 'unit': 'ticks'}, 'scale': 1}, {'column': {'key': 'candidate_net_family_low', 'label': 'Familywise mean low', 'format': 'number', 'precision': 2, 'unit': 'ticks'}, 'scale': 1}, {'column': {'key': 'candidate_net_family_high', 'label': 'Familywise mean high', 'format': 'number', 'precision': 2, 'unit': 'ticks'}, 'scale': 1}, {'column': {'key': 'difference', 'label': 'Candidate minus control', 'format': 'number', 'precision': 2, 'unit': 'ticks'}, 'scale': 1}, {'column': {'key': 'family_ci_low', 'label': 'Familywise difference low', 'format': 'number', 'precision': 2, 'unit': 'ticks'}, 'scale': 1}, {'column': {'key': 'family_ci_high', 'label': 'Familywise difference high', 'format': 'number', 'precision': 2, 'unit': 'ticks'}, 'scale': 1}], 'where': {'segment': ['asia', 'london', 'new_york']}, 'description': 'All saved rows'}, {'kind': 'table', 'id': 'countertrend-example', 'title': 'NQ 10: two-more-bar colour probabilities', 'file': 'tables/08_summary.csv', 'columns': [{'column': {'key': 'segment', 'label': 'segment'}, 'scale': 1}, {'column': {'key': 'direction', 'label': 'Direction (1 bullish, −1 bearish)'}, 'scale': 1}, {'column': {'key': 'numerator', 'label': 'numerator', 'format': 'number', 'precision': 0}, 'scale': 1}, {'column': {'key': 'denominator', 'label': 'denominator', 'format': 'number', 'precision': 0}, 'scale': 1}, {'column': {'key': 'estimate', 'label': 'Rate', 'format': 'percent', 'precision': 1}, 'scale': 0.01}, {'column': {'key': 'baseline_estimate', 'label': 'Other-segment rate', 'format': 'percent', 'precision': 1}, 'scale': 0.01}, {'column': {'key': 'difference', 'label': 'Difference', 'format': 'number', 'precision': 2, 'unit': 'pp'}, 'scale': 1}, {'column': {'key': 'family_ci_low', 'label': 'Familywise low', 'format': 'number', 'precision': 2, 'unit': 'pp'}, 'scale': 1}, {'column': {'key': 'family_ci_high', 'label': 'Familywise high', 'format': 'number', 'precision': 2, 'unit': 'pp'}, 'scale': 1}], 'where': {'product': ['NQ'], 'setting': ['10'], 'segment': ['asia', 'london', 'new_york']}, 'description': 'NQ 10 illustration, both directions and every primary segment'}, {'kind': 'table', 'id': 'confirmation-example', 'title': 'NQ 10 bearish: two distinct control comparisons', 'file': 'tables/09_summary.csv', 'columns': [{'column': {'key': 'segment', 'label': 'segment'}, 'scale': 1}, {'column': {'key': 'denominator', 'label': 'Confirmed eligible n', 'format': 'number', 'precision': 0}, 'scale': 1}, {'column': {'key': 'estimate', 'label': 'Confirmed rate', 'format': 'percent', 'precision': 1}, 'scale': 0.01}, {'column': {'key': 'ordinary_baseline_denominator', 'label': 'Ordinary control n', 'format': 'number', 'precision': 0}, 'scale': 1}, {'column': {'key': 'ordinary_baseline_estimate', 'label': 'Ordinary rate', 'format': 'percent', 'precision': 1}, 'scale': 0.01}, {'column': {'key': 'ordinary_difference', 'label': 'Ordinary difference', 'format': 'number', 'precision': 2, 'unit': 'pp'}, 'scale': 1}, {'column': {'key': 'ordinary_family_ci_low', 'label': 'Familywise ordinary low', 'format': 'number', 'precision': 2, 'unit': 'pp'}, 'scale': 1}, {'column': {'key': 'ordinary_family_ci_high', 'label': 'Familywise ordinary high', 'format': 'number', 'precision': 2, 'unit': 'pp'}, 'scale': 1}, {'column': {'key': 'other_difference', 'label': 'Other-segment difference', 'format': 'number', 'precision': 2, 'unit': 'pp'}, 'scale': 1}, {'column': {'key': 'other_family_ci_low', 'label': 'Familywise other low', 'format': 'number', 'precision': 2, 'unit': 'pp'}, 'scale': 1}, {'column': {'key': 'other_family_ci_high', 'label': 'Familywise other high', 'format': 'number', 'precision': 2, 'unit': 'pp'}, 'scale': 1}], 'where': {'product': ['NQ'], 'setting': ['10'], 'direction': ['-1'], 'segment': ['asia', 'london', 'new_york']}, 'description': 'Explicit bearish NQ 10 illustration; do not generalize to all settings'}, {'kind': 'text', 'id': 'methods', 'title': 'Definitions and methods', 'body': 'Asia is 18:00–03:00, London 03:00–09:30 and New York 09:30–16:00 in inferred New York time. Transition is excluded from primary screening. The overlay source is 20260924T145715Z_session_v1; upstream cohorts remain separately attributed to 07: 20260924T004900Z_rxv07, 08: 20260924T132916Z_ctbars_v1 and 09: 20260924T141810Z_c2confirm_v1. Study 07 retains its older pre-normalization cohort and uses corrected clocks only for segment labels. Its estimate is mean signed proxy price after a two-tick executed-trade haircut. Studies 08 and 09 rates use C1 and confirmed-C2 denominators respectively. Their saved percentage-valued cells are converted to ratios for display; saved differences are already percentage points. Bounds retain the original overlay family corrections. The ordinary and other-segment controls answer different questions.', 'source': 'source-snapshot/plan.md', 'anchor': 'Definitions and methods'}, {'kind': 'text', 'id': 'limitations', 'title': 'Limitations and uncertainty', 'body': 'The short Study 07 and long Study 08/09 histories are unequal and previously viewed. Segments and chart settings are correlated. A comparison against ordinary bars is not evidence of segment-specific lift; the latter requires the separate other-segment contrast. Clock inference, retrospective exclusions, completion proxies and absent fill/cost evidence limit these to descriptive chart-price paths.', 'source': 'report.md', 'anchor': 'Limitations and uncertainty'}]}
EXPECTED = {'runs/10_range_xv_session_overlay/20260924T145715Z_session_v1/tables/09_summary.csv': 'c8d8a7a0e55c300c83bddb1e8321cd92fbb1d4ad74c7e12cac1d33a0ddf7a906', 'runs/10_range_xv_session_overlay/20260924T145715Z_session_v1/report.md': 'd9714bce62ca6ae4449de594ad9e33f7c18d45f57c0f22270ed022a28bce0c5a', 'runs/10_range_xv_session_overlay/20260924T145715Z_session_v1/manifest.json': '9354b839d4def8bca81da7ad2998d55bb018c1473b80b524688d43b5bb35b970', 'runs/10_range_xv_session_overlay/20260924T145715Z_session_v1/inputs.lock.json': 'c25d0373212e7d03df48e6cf9ed4e1b1273bd741e42e28263041bae4ea3cf664', 'runs/10_range_xv_session_overlay/20260924T145715Z_session_v1/source-snapshot/plan.md': '88674c2bb6873a247a16aa4a3a58a364f86d05f908bc6299ab8ef8c5ac4865b9', 'runs/10_range_xv_session_overlay/20260924T145715Z_session_v1/config.json': '862a7ec1b4cb9285e026b82dca7bd298c849305cb268fd3ccb00bd391155a23d', 'runs/10_range_xv_session_overlay/20260924T145715Z_session_v1/metrics.json': 'f23443266526ee7d0128e1dfeca07450f9777b246b8eee8ff92e4c6daa809964', 'runs/10_range_xv_session_overlay/20260924T145715Z_session_v1/tables/08_summary.csv': '37c7e457e3c0a04130dcf2e852f3c9bc45bc18ffb9624d909fc0939bb31c3747', 'runs/10_range_xv_session_overlay/20260924T145715Z_session_v1/tables/07_summary.csv': 'ec69c3920c776806aff663fe9857d38cc3e30345d9e0220a5dbe7e04b4a3a8f3'}

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
