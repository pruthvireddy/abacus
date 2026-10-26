# Presentation-only exporter for 14_asia_session_vp_levels. No analytical imports.
SPEC = {'study_id': '14_asia_session_vp_levels', 'source_run_id': '20260929T124500Z_asiavp_b2', 'publication_id': '14-asia-session-vp-levels-20261006-web', 'title': 'Asia volume-profile levels: the original three setups', 'summary': 'The original A–C protocol studies POC reversal, value-boundary retest and pre-touch HVN fade on NQ. Matched-control evidence is mixed; later D/E extensions are excluded.', 'selection': 'Publication-only choice', 'reason': 'Original protocol 1.0.0 A–C evidence directly answers the registered scope; later D/E exploratory extensions remain separately attributed and outside this featured page.', 'sources': ['report.md', 'config.json', 'manifest.json', 'inputs.lock.json', 'metrics.json', 'source/studies/14_asia_session_vp_levels/protocol-1.0.0.md'], 'sections': [{'kind': 'text', 'id': 'question', 'title': 'Question and scope', 'body': 'This selected original protocol 1.0.0 run evaluates three NQ setups during 20:00–00:00 New York time: A, a confirmed reversal toward prior RTH POC after a VAH/VAL excursion; B, developing Asia value-boundary break and retest; C, a fade at a pre-touch selected HVN. The publication emphasizes validation 2024–2025 with a fixed thirty-minute horizon.', 'source': 'report.md', 'anchor': 'Question and scope'}, {'kind': 'text', 'id': 'findings', 'title': 'Supported findings', 'body': 'POC reversal contrasts are inconclusive. The short-side value-boundary retest has favorable matched excursion evidence, while the short-side HVN fade has worse adverse excursion. Results differ by setup and side. They remain exploratory descriptive paths; this page does not incorporate the separate D/E extension.', 'source': 'report.md', 'anchor': 'Supported findings'}, {'kind': 'table', 'id': 'paths', 'title': 'Validation: original primary thirty-minute paths', 'file': 'tables/metrics.csv', 'columns': [{'column': {'key': 'setup', 'label': 'setup'}, 'scale': 1}, {'column': {'key': 'direction', 'label': 'direction'}, 'scale': 1}, {'column': {'key': 'events', 'label': 'events', 'format': 'number', 'precision': 0}, 'scale': 1}, {'column': {'key': 'complete', 'label': 'Complete paths', 'format': 'number', 'precision': 0}, 'scale': 1}, {'column': {'key': 'censored', 'label': 'censored', 'format': 'number', 'precision': 0}, 'scale': 1}, {'column': {'key': 'sessions', 'label': 'sessions', 'format': 'number', 'precision': 0}, 'scale': 1}, {'column': {'key': 'support', 'label': 'support'}, 'scale': 1}, {'column': {'key': 'mfe_points_mean', 'label': 'Mean MFE', 'format': 'number', 'precision': 2, 'unit': 'points'}, 'scale': 1}, {'column': {'key': 'mae_points_mean', 'label': 'Mean MAE', 'format': 'number', 'precision': 2, 'unit': 'points'}, 'scale': 1}, {'column': {'key': 'terminal_points_mean', 'label': 'Mean terminal change', 'format': 'number', 'precision': 2, 'unit': 'points'}, 'scale': 1}], 'where': {'split': ['validation'], 'variant': ['primary'], 'horizon': ['30']}, 'description': 'Both sides of A/B/C, validation primary fixed horizon'}, {'kind': 'table', 'id': 'controls', 'title': 'Validation: candidate minus matched controls', 'file': 'tables/control_effects.csv', 'columns': [{'column': {'key': 'setup', 'label': 'setup'}, 'scale': 1}, {'column': {'key': 'direction', 'label': 'direction'}, 'scale': 1}, {'column': {'key': 'events', 'label': 'events', 'format': 'number', 'precision': 0}, 'scale': 1}, {'column': {'key': 'matched', 'label': 'matched', 'format': 'number', 'precision': 0}, 'scale': 1}, {'column': {'key': 'unmatched', 'label': 'unmatched', 'format': 'number', 'precision': 0}, 'scale': 1}, {'column': {'key': 'mfe_difference_mean', 'label': 'MFE difference', 'format': 'number', 'precision': 2, 'unit': 'points'}, 'scale': 1}, {'column': {'key': 'mfe_ci_lower', 'label': '95% MFE low', 'format': 'number', 'precision': 2, 'unit': 'points'}, 'scale': 1}, {'column': {'key': 'mfe_ci_upper', 'label': '95% MFE high', 'format': 'number', 'precision': 2, 'unit': 'points'}, 'scale': 1}, {'column': {'key': 'mae_difference_mean', 'label': 'MAE difference', 'format': 'number', 'precision': 2, 'unit': 'points'}, 'scale': 1}, {'column': {'key': 'mae_ci_lower', 'label': '95% MAE low', 'format': 'number', 'precision': 2, 'unit': 'points'}, 'scale': 1}, {'column': {'key': 'mae_ci_upper', 'label': '95% MAE high', 'format': 'number', 'precision': 2, 'unit': 'points'}, 'scale': 1}], 'where': {'split': ['validation']}, 'description': 'All saved rows'}, {'kind': 'table', 'id': 'coverage', 'title': 'Saved input coverage by year', 'file': 'tables/quality_by_year.csv', 'columns': [{'column': {'key': 'year', 'label': 'year', 'format': 'number', 'precision': 0}, 'scale': 1}, {'column': {'key': 'source_dates', 'label': 'source dates', 'format': 'number', 'precision': 0}, 'scale': 1}, {'column': {'key': 'complete_futures_sessions', 'label': 'Complete futures sessions', 'format': 'number', 'precision': 0}, 'scale': 1}, {'column': {'key': 'missing_evening_minutes', 'label': 'Missing evening minutes', 'format': 'number', 'precision': 0}, 'scale': 1}, {'column': {'key': 'complete_six_hour_evenings', 'label': 'Complete six-hour evenings', 'format': 'number', 'precision': 0}, 'scale': 1}], 'where': {}, 'description': 'All saved rows'}, {'kind': 'text', 'id': 'methods', 'title': 'Definitions and methods', 'body': 'A is a confirmed reversal toward POC after an upper/lower excursion, not a generic value-area reentry rule. B confirms a retest of developing VAH/VAL. C selects its overhead/below HVN before the touch and counts actual range contact, not a gap crossing. Entry references are next one-minute opens; thirty-minute paths remain within the midnight deadline. Volume profiles allocate bar volume uniformly across price bins, an approximation rather than trade-by-trade volume at price. Matched controls share year, side, New York hour and development volatility quintile. Positive MFE differences favor the candidate; positive MAE differences mean more adverse excursion. Saved 95% intervals use two-week moving ISO-week bootstrap blocks. A variable midnight deadline is separate and excluded here.', 'source': 'source/studies/14_asia_session_vp_levels/protocol-1.0.0.md', 'anchor': 'Definitions and methods'}, {'kind': 'text', 'id': 'limitations', 'title': 'Limitations and uncertainty', 'body': 'Older years have sparse one-minute source coverage; the saved quality rows disclose it. Historical 2010–2019, development 2020–2023, validation 2024–2025 and 2026 YTD are chronological diagnostics, not pristine confirmation. Adjustment mapping and whole-day eligibility are retrospective. Bar-volume profiles, intrabar ordering and live fills lack independent indicator/execution parity. An original event-ledger manifest is absent; saved report, configuration and artifact ledgers still provide bounded presentation provenance.', 'source': 'report.md', 'anchor': 'Limitations and uncertainty'}]}
EXPECTED = {'runs/14_asia_session_vp_levels/20260929T124500Z_asiavp_b2/metrics.json': '1dc4e5bb4011c009c70cb694bfcccabf3455c974763f1521e1198823487c0869', 'runs/14_asia_session_vp_levels/20260929T124500Z_asiavp_b2/tables/quality_by_year.csv': 'eef7e812ce9c66074a9ed7b5b073bd07137262765261c639e015773891fa1d48', 'runs/14_asia_session_vp_levels/20260929T124500Z_asiavp_b2/report.md': '08de259613d5ef711173067899839802aa790199a84d36cc47eae413fe62c072', 'runs/14_asia_session_vp_levels/20260929T124500Z_asiavp_b2/tables/control_effects.csv': 'c081a4ae84a7beeedc77bfae1592f9169e6ab14585b258ab0d6125317a98b6b0', 'runs/14_asia_session_vp_levels/20260929T124500Z_asiavp_b2/config.json': '569fe630ba77a518d26658e7d20d17c546df2b6ea162a0a7685a436e4ba15f0a', 'runs/14_asia_session_vp_levels/20260929T124500Z_asiavp_b2/manifest.json': 'e697a1f2d0f8dd2bd3d990481e137289938d44390645a2f6b9da0c0f0e538c0d', 'runs/14_asia_session_vp_levels/20260929T124500Z_asiavp_b2/inputs.lock.json': '9af2fbbca830884796801c5a28a0d8f0d68ccae07f67a8a7fd6d9be2d6112742', 'runs/14_asia_session_vp_levels/20260929T124500Z_asiavp_b2/tables/metrics.csv': '6ce03ffba721c46c3e736267dae16d8633be70df981b2fd7a7cc26f11bbd4227', 'runs/14_asia_session_vp_levels/20260929T124500Z_asiavp_b2/source/studies/14_asia_session_vp_levels/protocol-1.0.0.md': '9680472d76419fe2740b585603ea7e3ca2895fdeadba24f44537d57809f0ebd8'}

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
