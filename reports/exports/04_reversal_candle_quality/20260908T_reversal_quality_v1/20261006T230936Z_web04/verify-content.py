"""Check the saved-cell transfer and hashes independently of research code."""
import csv,hashlib,json,importlib.util
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[4]
publication=json.loads((HERE/'publication.json').read_text());mapping=json.loads((HERE/'source-map.json').read_text())
sections={s['id']:s for s in publication['sections']};cache={};numeric=0;seen=set()
for source in mapping['sources']:
 assert hashlib.sha256((ROOT/source['path']).read_bytes()).hexdigest()==source['sha256'],source['path']
for b in mapping['bindings']:
 if b['source'] not in cache:cache[b['source']]=list(csv.DictReader((ROOT/b['source']).open()))
 raw=cache[b['source']][b['data_row_1_based']-1][b['source_column']];assert raw==b['source_raw']
 s=sections[b['section']];c=next(c for c in s['columns'] if c['key']==b['column']);v=s['rows'][b['output_row']][b['column']]
 if raw=='':expected=None
 elif c.get('format'):expected=float(raw)*b['scale'];numeric+=1
 elif raw in ['True','False']:expected=raw=='True'
 else:expected=raw if c['key'].startswith('metric_id') else raw.replace('_',' ')
 assert v==expected==b['value'],b
 seen.add((s['id'],b['output_row'],b['column']))
assert len(seen)==sum(len(s['rows'])*len(s['columns']) for s in sections.values() if s['kind']=='table')
# Reconstruct with the retained exporter, rooted at the workspace, without writing.
spec=importlib.util.spec_from_file_location('frozen_exporter',HERE/'provenance/publish_web.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);module.ROOT=ROOT
pub,source_map=module.prepare(HERE.name);assert pub==publication and source_map==mapping
superseded=publication['id'].startswith(('08-','10-')) and not publication['id'].endswith('-r2')
record={'result':'passed','publication_id':publication['id'],'cell_bindings_checked':len(seen),'numeric_cells_checked':numeric,'source_hashes_checked':len(mapping['sources']),'complete_table_cell_coverage':True,'reconstruction_matches':True,'statistical_calculations_performed':False,'semantic_review':'Superseded: original baseline wording was incorrect; featured r2 corrects it and app navigation warns readers.' if superseded else 'Reviewed against saved reports/protocols; negative, inconclusive, exploratory, historical and price-path qualifications retained.','figure_review':'Table-first selection; no new figures or raster conversions. Existing pilots preserved.'}
(HERE/'content-verification.json').write_text(json.dumps(record,indent=2)+'\n');print(publication['id'],numeric,'numeric cells,',len(seen),'total bindings')
