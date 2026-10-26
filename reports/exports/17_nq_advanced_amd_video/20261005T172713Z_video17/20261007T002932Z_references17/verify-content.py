# Independent source-cell and byte audit. No analytical code or calculations.
import csv, hashlib, importlib.util, json, math, os, re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parent
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
m = json.loads((OUT/'source-map.json').read_text()); pub = json.loads((OUT/'publication.json').read_text())
cache = {}
def rows(path):
    if path not in cache:
        with (ROOT/path).open(newline='') as f: cache[path] = list(csv.DictReader(f))
    return cache[path]
for source in m['sources']: assert sha(ROOT/source['path']) == source['sha256'], source['path']
sections = {s['id']:s for s in pub['sections']}
for b in m['bindings']:
    raw=rows(b['source'])[b['data_row_1_based']-1][b['source_column']]
    assert raw==b['source_raw']
    c=next(c for c in sections[b['section']]['columns'] if c['key']==b['column'])
    expected=None if raw=='' else float(raw) if c.get('format') else (raw=='True') if raw in ['True','False'] else raw
    assert sections[b['section']]['rows'][b['output_row']][b['column']]==expected==b['value']
    if isinstance(expected,float): assert math.isfinite(expected)
    if c.get('format')=='percent' and expected is not None: assert 0<=expected<=1
if m['bindings']:
    assert len(m['bindings'])==sum(len(s['rows'])*len(s['columns']) for s in pub['sections'] if s['kind']=='table')
cells=0
for d in pub.get('downloads',[]):
    path=OUT/d['path']; assert sha(path)==d['sha256']; actual=rows(str(path.relative_to(ROOT)))
    assert len(actual)==d['rowCount']
    assert sha(ROOT/'runs'/m['study_id']/m['source_run_id']/d['source']['artifact'])==d['source']['sha256']
    dm=next(x for x in m['downloads'] if x['path']==d['path'])
    assert len(dm['cells'])==len(actual)*len(d['columns'])
    for b in dm['cells']:
        raw=rows(b['source'])[b['data_row_1_based']-1][b['column']]
        assert raw==b['source_raw']==actual[b['output_row']][b['column']]; cells+=1
    selected=[r for r in rows(dm['cells'][0]['source']) if all(r[k] in vals for k,vals in dm['selection'].items())]
    assert [{k:r[k] for k in d['columns']} for r in selected]==actual
for f in m['figures']:
    assert sha(OUT/f['path'])==f['output_sha256']
    if f.get('source_sha256'): assert sha(ROOT/f['source'])==f['source_sha256']
    for b in f.get('bindings',[]): assert rows(b['source'])[b['data_row_1_based']-1][b['column']]==b['raw'] and float(b['raw'])==b['value']
    if f['operation']=='Byte-identical raster copy': assert (ROOT/f['source']).read_bytes()==(OUT/f['path']).read_bytes()
qualitative=0
if 'preserved_pilot_source_map' in m:
    old=m['preserved_pilot_source_map']; t=old['table']; ledger=sections[t['section_id']]['rows']; byid={r['claim_id']:r for r in rows(t['source'])}
    for actual, cid in zip(ledger,t['claim_ids']):
        src=byid[cid]; assert actual=={'claim':cid+' · '+src['claim_summary'],'attribution':src['attribution'].replace('_',' '),'status':src['evidence_status'].replace('_',' '),'qualification':src['qualification']};qualitative+=1
    source=json.loads((ROOT/'runs'/m['study_id']/m['source_run_id']/'source.json').read_text())
    report=(ROOT/'runs'/m['study_id']/m['source_run_id']/'report.md').read_text()
    for ref in pub['references']:
        assert ref['title']==source['title'] and ref['creator']==source['creator']
        assert ref['publishedOn']==source['publication_date_as_displayed'] and ref['accessedOn']==source['access_date']
        if 'startSeconds' in ref:
            assert ref['url'] in report
            def time(x): return str(x//60)+':'+str(x%60).zfill(2)
            assert time(ref['startSeconds'])+'–'+time(ref['endSeconds']) in report
        else: assert ref['url']==source['url']
# Recreate presentation objects, exact projections and raster bytes using the retained authoring snapshot.
sp=importlib.util.spec_from_file_location('frozen_author',OUT/'provenance/publish_evidence.py');engine=importlib.util.module_from_spec(sp);sp.loader.exec_module(engine);engine.ROOT=ROOT
expected_pub,expected_map=engine.build(m['revision_id'],OUT,True)
assert pub==expected_pub and m==expected_map
record={'publication_id':pub['id'],'checks_passed':True,'source_artifacts':len(m['sources']),'displayed_table_cells':len(m['bindings']),'download_cells':cells,'download_files':len(pub.get('downloads',[])),'figure_value_bindings':sum(len(f.get('bindings',[])) for f in m['figures']),'figure_files':len(m['figures']),'qualitative_claim_rows':qualitative,'operations':'Saved-cell identity, explicit row/column selection, exact string CSV projection, unchanged qualitative ledger/attribution, source/asset hashes and deterministic raster verification. No research execution.'}
(OUT/'content-verification.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record))
