SPEC = {'study_id': '17_nq_advanced_amd_video', 'source_run_id': '20261005T172713Z_video17', 'protocol': '1.0.0', 'publication_id': 'nq-amd-source-review-20261007-references', 'published_at': '2026-10-07T00:29:32Z', 'sources': ['report.md', 'config.json', 'manifest.json', 'inputs.lock.json', 'metrics.json', 'source.json', 'tables/charts.csv', 'tables/claims.csv'], 'selection': 'Publication-only selection retained', 'reason': 'Retain the explicitly selected Phase 3 source; this is a presentation revision of the same evidence.', 'source_references': {}, 'source_titles': {}, 'downloads': [], 'figures': [{'source': 'figures/01_weekly_context.jpg', 'path': 'figures/01_weekly_context.jpg'}, {'source': 'figures/06_wednesday_ob_chain.jpg', 'path': 'figures/06_wednesday_ob_chain.jpg'}, {'source': 'figures/09_thursday_no_trade.jpg', 'path': 'figures/09_thursday_no_trade.jpg'}, {'source': 'figures/11_friday_news_distribution.jpg', 'path': 'figures/11_friday_news_distribution.jpg'}, {'source': 'figures/13_friday_target_shortfall.jpg', 'path': 'figures/13_friday_target_shortfall.jpg'}], 'reference_provenance': {'source.json': 'Video identity, creator, publication/access dates', 'report.md': 'Existing timestamped source links under weekly, Wednesday, Thursday, Friday and shortfall sections; no new source investigation.'}, 'title': 'NQ advanced AMD: source examples and their limits', 'reader_need': 'Make the already saved lesson attribution and media ranges clickable without changing its qualitative interpretation.', 'base_publication': 'reports/exports/17_nq_advanced_amd_video/20261005T172713Z_video17/20261006T210008Z_web17/publication.json', 'base_map': 'reports/exports/17_nq_advanced_amd_video/20261005T172713Z_video17/20261006T210008Z_web17/source-map.json', 'additional_sources': ['reports/exports/17_nq_advanced_amd_video/20261005T172713Z_video17/20261006T210008Z_web17/publication.json', 'reports/exports/17_nq_advanced_amd_video/20261005T172713Z_video17/20261006T210008Z_web17/source-map.json'], 'external_references': [('weekly-context', 'Weekly higher-timeframe context', 153, 381, ['weekly-context', 'weekly-figure']), ('wednesday-entry', 'Wednesday: why confirmation matters', 854, 950, ['wednesday', 'wednesday-figure']), ('thursday-no-trade', 'Thursday: unclear structure and no trade', 1156, 1260, ['thursday', 'thursday-figure']), ('friday-revision', 'Friday: revised hypothesis after observed news response', 1263, 1403, ['friday', 'friday-figure']), ('target-shortfall', 'The unmet objective and later-week hypothesis', 1467, 1494, ['shortfall', 'shortfall-figure'])]}
PINNED = {'runs/17_nq_advanced_amd_video/20261005T172713Z_video17/config.json': 'bba55cb9e331eac65d5522c750c619076e8ec9f73014bf642fd793491137cb30', 'runs/17_nq_advanced_amd_video/20261005T172713Z_video17/figures/01_weekly_context.jpg': '3c58a33ad4303ac10a4c44e58423f0f4eb9b7873cdf6fe0c3d67b26f913dd362', 'runs/17_nq_advanced_amd_video/20261005T172713Z_video17/figures/06_wednesday_ob_chain.jpg': 'b94b10bc923cc3bc07531d25c1523ea2bc8645dcbeccdaa3156e949d1e71c202', 'runs/17_nq_advanced_amd_video/20261005T172713Z_video17/figures/09_thursday_no_trade.jpg': '774795cdccb861226ba22cb4cf6beeefc86a97e05beaa67067cb808290e8d889', 'runs/17_nq_advanced_amd_video/20261005T172713Z_video17/figures/11_friday_news_distribution.jpg': '7106b46203fad89d61056db157e5150a55244d99abe70ca570cfed91665e51f5', 'runs/17_nq_advanced_amd_video/20261005T172713Z_video17/figures/13_friday_target_shortfall.jpg': 'c5caad94094510f84e565ed473c6bb28ff2a40210196d2c6198e3a402b904e80', 'runs/17_nq_advanced_amd_video/20261005T172713Z_video17/inputs.lock.json': 'f4a71a11a3dd6433d3acebd985d2afe3ff266366bc30efa87387b9e4aa6a7e1a', 'runs/17_nq_advanced_amd_video/20261005T172713Z_video17/manifest.json': 'b847f39255ed09e77e7f7f9b1930a84b4f294bd0ef9733af7d1024e0053c8245', 'runs/17_nq_advanced_amd_video/20261005T172713Z_video17/metrics.json': 'd1da540a219c44f16271bae0d4c4c3fb7f7f31c4a63d5fccd81f51e19568cd23', 'runs/17_nq_advanced_amd_video/20261005T172713Z_video17/report.md': '2d6aa8bafc2efd8825f16daf172c9b5ef26109b9b0ed1f33143213427b53571b', 'runs/17_nq_advanced_amd_video/20261005T172713Z_video17/source.json': '45b18b52db6c8f9b91c3208d676b89c9aefc8c7fd3f11e44f0d999105ce2e2f7', 'runs/17_nq_advanced_amd_video/20261005T172713Z_video17/tables/charts.csv': 'dc761dd48dc06c06cbfb195c9a4fd5fc47eab462898696b7e7e38bbf02de27a1', 'runs/17_nq_advanced_amd_video/20261005T172713Z_video17/tables/claims.csv': 'f20c0f415bff0908bf85f175b561d169e213679d765769d211dc62842a6330ff', 'reports/exports/17_nq_advanced_amd_video/20261005T172713Z_video17/20261006T210008Z_web17/publication.json': '5a8b7b71f099351ba180acff6a55506b00daafd05bd6b0487142994b38563d9a', 'reports/exports/17_nq_advanced_amd_video/20261005T172713Z_video17/20261006T210008Z_web17/source-map.json': '54bb9aea028e4e32c6b0e4a039959a0255c841a8b2fdf041713a5d1bc41bea7f'}

# Presentation-only saved-evidence selector; no analytical or dataset imports.
import argparse, csv, hashlib, io, json, math, re, shutil, subprocess
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def dump(path, value): path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False)+'\n')
def value(raw, column):
    if raw == '': return None
    if column.get('format'):
        number = float(raw); assert math.isfinite(number); return number
    if raw in ['True', 'False']: return raw == 'True'
    return raw

def build(revision, out, checking=False):
    run = ROOT / 'runs' / SPEC['study_id'] / SPEC['source_run_id']
    for path, expected in PINNED.items(): assert digest(ROOT/path) == expected, path
    bindings=[]; downloads=[]; download_maps=[]; sections=[]; sources=set(SPEC['sources']); tables={}; claims=[]
    def select(file, where):
        sources.add(file)
        if file not in tables:
            with (run/file).open(newline='') as handle: tables[file]=list(csv.DictReader(handle))
        chosen=[(i,r) for i,r in enumerate(tables[file],1) if all(r[k] in values for k,values in where.items())]
        assert chosen, (file,where); return chosen
    def source_reference(id, file):
        return {'id':id, 'kind':'saved-artifact', 'label':Path(file).name, 'title':SPEC['source_titles'][file], 'runId':SPEC['source_run_id'], 'artifact':file, 'sha256':digest(run/file)}
    references=[source_reference(id,file) for id,file in SPEC['source_references'].items()]
    if SPEC.get('base_publication'):
        pub=json.loads((ROOT/SPEC['base_publication']).read_text())
        base_map=json.loads((ROOT/SPEC['base_map']).read_text())
        sections=pub['sections']; sources.update(['source.json','report.md','tables/charts.csv','tables/claims.csv','config.json','manifest.json','inputs.lock.json'])
        for item in sections:
            if item['id']=='sources':
                item['body'] = re.sub(r'Presentation revision \S+ uses web-study-report-1.0\.', f'Presentation revision {revision} uses web-study-report-1.1.', item['body'])
            if item['id']=='claim-ledger':
                item['description']='Selected source claims and saved review qualifications. These are not independently verified trades or a statistical scorecard.'
                item['notes']=['Source claims, chart observations and reviewer interpretations retain distinct evidence labels.']
        source=json.loads((run/'source.json').read_text())
        references=[{'id':'full-lesson','kind':'external','label':'Tmac’s full advanced AMD lesson','title':source['title'],'creator':source['creator'],'url':source['url'],'publishedOn':source['publication_date_as_displayed'],'accessedOn':source['access_date']}]
        for id,label,start,end,section_ids in SPEC['external_references']:
            references.append({'id':id,'kind':'external','label':label,'title':source['title'],'creator':source['creator'],'url':source['url']+f'&t={start}s','startSeconds':start,'endSeconds':end,'publishedOn':source['publication_date_as_displayed'],'accessedOn':source['access_date']})
            for item in sections:
                if item['id'] in section_ids: item['referenceIds']=[id]
        for item in sections:
            if item['id'] in ['question','sources','methods']: item['referenceIds']=['full-lesson']
        claims=base_map['claims']
    else:
        for item in SPEC['sections']:
            if item['kind']=='text':
                sections.append({k:item[k] for k in ['id','kind','title','body']})
                claims.append({'section':item['id'],'source':str((run/item.get('source','report.md')).relative_to(ROOT)), 'heading_or_scope':item.get('anchor','Saved executed report and protocol; faithful abridgment')})
            elif item['kind']=='table':
                selected=select(item['file'],item['where']); assert len(selected)<=100
                rows=[]
                for row_number,raw in selected:
                    row={}
                    for c in item['columns']:
                        row[c['key']]=value(raw[c['key']],c)
                        bindings.append({'section':item['id'],'output_row':len(rows),'column':c['key'],'source':str((run/item['file']).relative_to(ROOT)),'data_row_1_based':row_number,'source_column':c['key'],'source_raw':raw[c['key']],'value':row[c['key']],'scale':1})
                    rows.append(row)
                sections.append({**{k:item[k] for k in ['id','kind','title','description','notes','referenceIds']},'columns':item['columns'],'rows':rows})
        pub={'title':SPEC['title'],'summary':SPEC['summary'],'source':{'producer':'sahadeva','runId':SPEC['source_run_id']},'sections':sections}
    for spec in SPEC['downloads']:
        chosen=select(spec['file'],spec['where']);assert len(chosen)<=1000
        stream=io.StringIO(newline='');writer=csv.writer(stream,lineterminator='\n');writer.writerow(spec['columns'])
        cell_map=[]
        for i,(row_number,row) in enumerate(chosen):
            writer.writerow([row[k] for k in spec['columns']])
            for key in spec['columns']:cell_map.append({'output_row':i,'column':key,'source':str((run/spec['file']).relative_to(ROOT)),'data_row_1_based':row_number,'source_raw':row[key]})
        data=stream.getvalue().encode('utf-8');path='downloads/'+spec['filename']
        if checking: assert (out/path).read_bytes()==data,path
        else: (out/'downloads').mkdir(exist_ok=True);(out/path).write_bytes(data)
        downloads.append({**{k:spec[k] for k in ['id','label','description','population','units','scope','columns']},'path':path,'mediaType':'text/csv','rowCount':len(chosen),'sha256':hashlib.sha256(data).hexdigest(),'source':{'runId':SPEC['source_run_id'],'artifact':spec['file'],'sha256':digest(run/spec['file'])}})
        download_maps.append({'path':path,'selection':spec['where'],'operation':'Projection of explicitly selected saved rows/columns; exact source CSV strings, no new statistics.','cells':cell_map})
    figures=[];jobs=[]
    for spec in SPEC['figures']:
        source=spec['source'];target=spec['path'];sources.add(source)
        if target.endswith('.jpg'):
            if checking: assert (out/target).read_bytes()==(run/source).read_bytes()
            else: (out/'figures').mkdir(exist_ok=True);shutil.copyfile(run/source,out/target)
        else: jobs.append({'source':str((run/source).relative_to(ROOT)),'output':target})
        if not SPEC.get('base_publication'):sections.insert(next(i for i,s in enumerate(sections) if s['id']=='methods'),{k:spec[k] for k in ['id','kind','title','path','alt','caption','referenceIds']})
        figures.append({'path':target,'source':str((run/source).relative_to(ROOT)),'source_sha256':digest(run/source),'operation':'Byte-identical raster copy' if target.endswith('.jpg') else 'Faithful SVG rasterization at 1800px width, white background; no crop or data change.'})
    if SPEC.get('annual_chart'):
        chosen=select('tables/yearly.csv',{'cooldown':['10'],'horizon':['20']})
        svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="960" viewBox="0 0 1600 960"><rect width="1600" height="960" fill="white"/><g font-family="Arial" fill="#253d35"><text x="100" y="65" font-size="36">GC: saved annual excursion means and intervals</text><text x="100" y="110" font-size="23">10-bar cooldown · 20 five-minute bars (100 minutes) · GC points</text>']
        for tick in range(0,46,5):
            y=790-tick*13;svg.append(f'<line x1="100" x2="1540" y1="{y}" y2="{y}" stroke="#d4d8cd"/><text x="85" y="{y+8}" text-anchor="end" font-size="22">{tick}</text>')
        plot_bindings=[]
        for i,(row_number,r) in enumerate(chosen):
            x=135+i*86
            svg.append(f'<text x="{x}" y="825" text-anchor="middle" font-size="20">{r["year"]}</text>')
            for offset,prefix,color,label in [(-11,'mae','#7e4b35','Adverse'),(11,'mfe','#376d57','Favorable')]:
                mean=float(r['mean_'+prefix]);low=float(r['mean_'+prefix+'_ci_low']);high=float(r['mean_'+prefix+'_ci_high'])
                svg.append(f'<line x1="{x+offset}" x2="{x+offset}" y1="{790-high*13:.4f}" y2="{790-low*13:.4f}" stroke="{color}" stroke-width="3"/><circle cx="{x+offset}" cy="{790-mean*13:.4f}" r="6" fill="{color}"/>')
                for key in ['mean_'+prefix,'mean_'+prefix+'_ci_low','mean_'+prefix+'_ci_high']:plot_bindings.append({'source':str((run/'tables/yearly.csv').relative_to(ROOT)),'data_row_1_based':row_number,'column':key,'raw':r[key],'value':float(r[key])})
        svg.extend(['<text x="100" y="880" font-size="24" fill="#7e4b35">● MAE (adverse)</text><text x="400" y="880" font-size="24" fill="#376d57">● MFE (favorable)</text><text x="100" y="920" font-size="22">Approximate 95% ISO-week normal cluster intervals; 2010 partial, 2026 YTD.</text></g></svg>'])
        data=''.join(svg).encode();local='provenance/yearly.svg'
        if checking:assert (out/local).read_bytes()==data
        else:(out/local).write_bytes(data)
        jobs.append({'source':str((out/local).relative_to(ROOT)),'output':'figures/yearly-excursions.png'})
        sections.insert(2,{'kind':'figure','id':'yearly-figure','title':'Annual path scale at the saved default','path':'figures/yearly-excursions.png','alt':'Separate adverse and favorable annual GC excursion means with saved interval endpoints; both increase markedly in 2025 and 2026.','caption':'Exact yearly.csv values at cooldown 10 and horizon 20. Dots are means; vertical lines are approximate 95% normal ISO-week cluster intervals, unadjusted for multiple comparisons. GC points; 2010 partial and 2026 YTD. Extrema have unknown ordering and are not executable exits.','referenceIds':['yearly-source']})
        figures.append({'path':'figures/yearly-excursions.png','source':str((run/'tables/yearly.csv').relative_to(ROOT)),'operation':'Draw saved annual means and saved interval endpoints; only affine pixel projection, no estimates, smoothing or aggregation.','bindings':plot_bindings})
    if jobs:
        if not checking:
            (out/'figures').mkdir(exist_ok=True)
            dump(out/'provenance/figure-jobs.json',jobs)
        else:assert json.loads((out/'provenance/figure-jobs.json').read_text())==jobs
        renderer = out/'provenance/render_web_figures.mjs' if checking else ROOT/'studies'/SPEC['study_id']/'render_web_figures.mjs'
        command=['node',str(renderer),'--workspace-root',str(ROOT),'--revision',revision]
        if checking:command.append('--check')
        subprocess.run(command,check=True)
    for f in figures:f['output_sha256']=digest(out/f['path'])
    if not SPEC.get('base_publication'):sections.append({'id':'sources-provenance','kind':'text','title':'Source-run and presentation provenance','body':f"Study {SPEC['study_id']}. Source run {SPEC['source_run_id']}; executed protocol {SPEC['protocol']}. Presentation {revision}. Saved summary artifacts and selected figure bytes retain their recorded identities. Research evidence and qualifications are unchanged."})
    pub.update({'schemaVersion':'1.1','id':SPEC['publication_id'],'publishedAt':SPEC['published_at'],'references':references})
    if downloads:pub['downloads']=downloads
    source_records=[{'path':str((run/s).relative_to(ROOT)),'sha256':digest(run/s)} for s in sorted(sources)]
    for s in SPEC.get('additional_sources',[]):source_records.append({'path':s,'sha256':digest(ROOT/s)})
    mapping={'study_id':SPEC['study_id'],'source_run_id':SPEC['source_run_id'],'revision_id':revision,'publication_id':SPEC['publication_id'],'source_selection':SPEC['selection'],'reason':SPEC['reason'],'sources':source_records,'bindings':bindings,'claims':claims,'downloads':download_maps,'figures':figures,'references':SPEC.get('reference_provenance',{})}
    if SPEC.get('base_publication'):mapping['preserved_pilot_source_map']=base_map
    return pub,mapping

if __name__=='__main__':
    parser=argparse.ArgumentParser(description='Prepare only selected saved evidence. Never run analysis.');parser.add_argument('--revision',required=True);parser.add_argument('--check',action='store_true');args=parser.parse_args()
    assert re.fullmatch(r'[A-Za-z0-9_-]+',args.revision)
    out=ROOT/'reports/exports'/SPEC['study_id']/SPEC['source_run_id']/args.revision
    if not args.check:out.mkdir(parents=True,exist_ok=False);(out/'provenance').mkdir()
    pub,mapping=build(args.revision,out,args.check)
    if args.check:assert json.loads((out/'publication.json').read_text())==pub;assert json.loads((out/'source-map.json').read_text())==mapping
    else:
        dump(out/'publication.json',pub);dump(out/'source-map.json',mapping);shutil.copyfile(__file__,out/'provenance/publish_evidence.py')
        renderer=ROOT/'studies'/SPEC['study_id']/'render_web_figures.mjs'
        if renderer.exists():shutil.copyfile(renderer,out/'provenance/render_web_figures.mjs')
        (out/'README.md').write_text(f"# {SPEC['title']}\n\n[Source](publication.json) · [Source map](source-map.json) · [Manifest](manifest.json) · [Verification](verification.json)\n\n{SPEC['reader_need']}\n\nSaved-evidence selection only. New immutable revision; no research execution. Exact source cells, figure conversions and CSV projections are recorded in the source map.\n")
    print(str(out.relative_to(ROOT)))
