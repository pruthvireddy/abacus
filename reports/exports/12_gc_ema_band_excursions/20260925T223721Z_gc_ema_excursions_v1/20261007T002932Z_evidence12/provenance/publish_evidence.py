SPEC = {'study_id': '12_gc_ema_band_excursions', 'source_run_id': '20260925T223721Z_gc_ema_excursions_v1', 'protocol': '1.0.0', 'publication_id': '12-gc-ema-band-excursions-20261007-evidence', 'published_at': '2026-10-07T00:29:32Z', 'sources': ['report.md', 'config.json', 'manifest.json', 'inputs.lock.json', 'metrics.json'], 'selection': 'Registered reference', 'reason': 'Retain the explicitly selected Phase 3 source; this is a presentation revision of the same evidence.', 'source_references': {'yearly-source': 'tables/yearly.csv', 'interval-definition': 'metrics.json'}, 'source_titles': {'tables/yearly.csv': 'Saved annual cohort, exclusion and excursion summary', 'metrics.json': 'Executed metric definitions, including approximate normal cluster mean intervals'}, 'downloads': [{'id': 'gc-cooldown10-year-horizon', 'file': 'tables/yearly.csv', 'where': {'cooldown': ['10']}, 'columns': ['year', 'cooldown', 'horizon', 'accepted_signals', 'valid_n', 'sessions', 'weeks', 'insufficient_future_bars', 'time_gap', 'partial_or_mixed_bar', 'contract_change', 'adjustment_change', 'mean_mae', 'mean_mae_ci_low', 'mean_mae_ci_high', 'mean_mfe', 'mean_mfe_ci_low', 'mean_mfe_ci_high', 'mean_terminal', 'mean_terminal_ci_low', 'mean_terminal_ci_high', 'terminal_positive_rate'], 'filename': 'gc-cooldown10-year-horizon.csv', 'label': 'GC annual and horizon evidence', 'population': 'GC lower outer-band accepted signals, cooldown 10; 2010 partial through 2026 YTD.', 'units': 'Price means/bounds: GC points. Rate: ratio. Horizon/cooldown: five-minute bars. Counts: saved signals, paths, sessions, weeks.', 'scope': 'All 17 saved years and seven horizons at cooldown 10; 119 separate cells.', 'description': 'Contains all seven saved horizons for every year, beyond the on-page annual horizon-20 and 2026 selections. Exclusions and saved mean bounds are included; no event ledger or other cooldown is included.'}], 'figures': [], 'reference_provenance': {}, 'title': 'GC EMA outer band: years, cohorts and path scale', 'summary': 'Saved GC excursion means, coverage and horizon-specific evidence at a ten-bar cooldown. Annual regimes differ; MAE/MFE extrema and terminal rates do not establish executable profits.', 'reader_need': 'Separate annual path scale, outcome denominators and exclusions; inspect exact saved horizon rows without the full research grid.', 'annual_chart': True, 'sections': [{'id': 'question', 'kind': 'text', 'title': 'Question and selected scope', 'body': 'A completed five-minute GC close at or below EMA225 minus three population standard deviations of signed close-minus-EMA residuals is followed from the next complete unadjusted open. The annual view fixes cooldown at ten following bars and horizon at twenty five-minute bars (100 minutes). The 2026 horizon view retains the saved seven horizons; it does not pool their outcomes.', 'source': 'report.md', 'anchor': 'Saved report narrative and executed protocol'}, {'kind': 'text', 'id': 'findings', 'title': 'Supported findings', 'body': 'The saved yearly table reports both adverse and favorable path extrema rather than choosing an MFE exit. Coverage, valid denominators and uncertainty differ by year. The larger cooldown/horizon grid is a correlated sensitivity, not independent replication or optimized trading evidence.', 'source': 'report.md', 'anchor': 'Supported findings'}, {'id': 'yearly', 'kind': 'table', 'title': 'Annual means and outcome support', 'file': 'tables/yearly.csv', 'where': {'cooldown': ['10'], 'horizon': ['20']}, 'columns': [{'key': 'year', 'label': 'Year'}, {'key': 'accepted_signals', 'label': 'Accepted signals', 'format': 'number', 'precision': 0}, {'key': 'valid_n', 'label': 'Complete paths', 'format': 'number', 'precision': 0}, {'key': 'sessions', 'label': 'Sessions', 'format': 'number', 'precision': 0}, {'key': 'weeks', 'label': 'ISO weeks', 'format': 'number', 'precision': 0}, {'key': 'mean_mae', 'label': 'Mean MAE', 'format': 'number', 'precision': 2, 'unit': 'GC points'}, {'key': 'mean_mae_ci_low', 'label': 'MAE 95% low', 'format': 'number', 'precision': 2, 'unit': 'GC points'}, {'key': 'mean_mae_ci_high', 'label': 'MAE 95% high', 'format': 'number', 'precision': 2, 'unit': 'GC points'}, {'key': 'mean_mfe', 'label': 'Mean MFE', 'format': 'number', 'precision': 2, 'unit': 'GC points'}, {'key': 'mean_mfe_ci_low', 'label': 'MFE 95% low', 'format': 'number', 'precision': 2, 'unit': 'GC points'}, {'key': 'mean_mfe_ci_high', 'label': 'MFE 95% high', 'format': 'number', 'precision': 2, 'unit': 'GC points'}], 'description': 'Each row is one signal-close calendar year at cooldown 10 / horizon 20. Accepted signals include subsequently unavailable paths; complete paths supply the outcome denominator.', 'notes': ['Mean intervals are approximate 95% normal cluster intervals by ISO week, unadjusted for multiple comparisons; metrics.json names this method.', '2010 begins midyear and 2026 is YTD through September 18. MAE/MFE are separate extrema with unknown ordering.'], 'referenceIds': ['yearly-source']}, {'id': 'terminal', 'kind': 'table', 'title': 'Annual terminal movement', 'file': 'tables/yearly.csv', 'where': {'cooldown': ['10'], 'horizon': ['20']}, 'columns': [{'key': 'year', 'label': 'Year'}, {'key': 'valid_n', 'label': 'Complete paths', 'format': 'number', 'precision': 0}, {'key': 'mean_terminal', 'label': 'Mean terminal', 'format': 'number', 'precision': 2, 'unit': 'GC points'}, {'key': 'mean_terminal_ci_low', 'label': '95% low', 'format': 'number', 'precision': 2, 'unit': 'GC points'}, {'key': 'mean_terminal_ci_high', 'label': '95% high', 'format': 'number', 'precision': 2, 'unit': 'GC points'}, {'key': 'terminal_positive_rate', 'label': 'Terminal positive', 'format': 'percent', 'precision': 1}], 'description': 'Terminal movement is horizon-close minus next-open entry, distinct from the path maximum or minimum. Terminal-positive rate uses complete paths.', 'notes': ['Mean intervals are approximate 95% normal cluster intervals by ISO week, unadjusted for multiple comparisons; metrics.json names this method.', '2010 begins midyear and 2026 is YTD through September 18. MAE/MFE are separate extrema with unknown ordering.'], 'referenceIds': ['yearly-source']}, {'id': 'exclusions', 'kind': 'table', 'title': 'Why accepted signals lack an annual outcome', 'file': 'tables/yearly.csv', 'where': {'cooldown': ['10'], 'horizon': ['20']}, 'columns': [{'key': 'year', 'label': 'Year'}, {'key': 'accepted_signals', 'label': 'Accepted', 'format': 'number', 'precision': 0}, {'key': 'valid_n', 'label': 'Valid', 'format': 'number', 'precision': 0}, {'key': 'insufficient_future_bars', 'label': 'Incomplete future', 'format': 'number', 'precision': 0}, {'key': 'time_gap', 'label': 'Time gap', 'format': 'number', 'precision': 0}, {'key': 'partial_or_mixed_bar', 'label': 'Partial / mixed', 'format': 'number', 'precision': 0}, {'key': 'contract_change', 'label': 'Contract change', 'format': 'number', 'precision': 0}, {'key': 'adjustment_change', 'label': 'Adjustment change', 'format': 'number', 'precision': 0}], 'description': 'Saved exclusion counts are copied at the same default. Missing paths are unavailable, rather than zero-return or failed trades.', 'notes': ['Do not sum across cooldowns or horizons: the same source observations can contribute repeatedly.'], 'referenceIds': ['yearly-source']}, {'id': 'horizons', 'kind': 'table', 'title': '2026 YTD: separate saved horizons', 'file': 'tables/yearly.csv', 'where': {'year': ['2026'], 'cooldown': ['10']}, 'columns': [{'key': 'horizon', 'label': 'Five-minute bars', 'format': 'number', 'precision': 0}, {'key': 'valid_n', 'label': 'Complete paths', 'format': 'number', 'precision': 0}, {'key': 'mean_mae', 'label': 'Mean MAE', 'format': 'number', 'precision': 2, 'unit': 'GC points'}, {'key': 'mean_mae_ci_low', 'label': 'MAE 95% low', 'format': 'number', 'precision': 2, 'unit': 'GC points'}, {'key': 'mean_mae_ci_high', 'label': 'MAE 95% high', 'format': 'number', 'precision': 2, 'unit': 'GC points'}, {'key': 'mean_mfe', 'label': 'Mean MFE', 'format': 'number', 'precision': 2, 'unit': 'GC points'}, {'key': 'mean_mfe_ci_low', 'label': 'MFE 95% low', 'format': 'number', 'precision': 2, 'unit': 'GC points'}, {'key': 'mean_mfe_ci_high', 'label': 'MFE 95% high', 'format': 'number', 'precision': 2, 'unit': 'GC points'}], 'description': 'These are separate per-horizon eligible populations at cooldown 10. A longer horizon has its own denominator and exclusions.', 'notes': ['Mean intervals are approximate 95% normal cluster intervals by ISO week, unadjusted for multiple comparisons; metrics.json names this method.', '2010 begins midyear and 2026 is YTD through September 18. MAE/MFE are separate extrema with unknown ordering.'], 'referenceIds': ['yearly-source']}, {'id': 'methods', 'kind': 'text', 'title': 'Definitions and methods', 'body': 'Cooldown C suppresses the C following bars after an accepted signal; suppressed candidates do not restart it. The next contiguous full five-minute bar supplies the unadjusted entry reference. Every measured future bar must be complete and keep one contract and adjustment. MAE is adverse excursion, MFE favorable excursion, and terminal movement is the final close minus entry. Saved mean bounds use approximate 95% normal ISO-week cluster intervals; no interval for terminal-positive rate is manufactured.', 'source': 'report.md', 'anchor': 'Saved report narrative and executed protocol'}, {'kind': 'text', 'id': 'limitations', 'title': 'Limitations and uncertainty', 'body': 'Coverage begins partway through 2010 and 2026 is YTD through September 18. Whole-day and adjusted continuous history eligibility is retrospective rather than point-in-time. Missing minutes, partial bars, gaps and roll/adjustment changes exclude paths. No stops, fees, fills, slippage or net profitability were tested; the saved interactive report is not imported into the public page.', 'source': 'report.md', 'anchor': 'Limitations and uncertainty'}]}
PINNED = {'runs/12_gc_ema_band_excursions/20260925T223721Z_gc_ema_excursions_v1/config.json': 'b66a43bc5340842f20d2af6a27c9f722e8a1e077bf6064b76c8300ecef9b180d', 'runs/12_gc_ema_band_excursions/20260925T223721Z_gc_ema_excursions_v1/inputs.lock.json': 'af1c6039073e52dffed9cb35cdd007ed3fc097e41762939e9a803d7dd08c8d87', 'runs/12_gc_ema_band_excursions/20260925T223721Z_gc_ema_excursions_v1/manifest.json': 'fa3c10ae5f931b7b793d1f1a9efc684ca5c6c4135090a3c0a1fe09c29a2999f3', 'runs/12_gc_ema_band_excursions/20260925T223721Z_gc_ema_excursions_v1/metrics.json': '73e07a890898ae38825c0f38ea10ba92894cc520c8299a5492ddf19ba1829b9e', 'runs/12_gc_ema_band_excursions/20260925T223721Z_gc_ema_excursions_v1/report.md': '46896e6e20ced611a743d4ff0bdc91da0ab3023327da54c56af689de601991e3', 'runs/12_gc_ema_band_excursions/20260925T223721Z_gc_ema_excursions_v1/tables/yearly.csv': '20993a93b12a82944ecbad0cfaf78bd3bda9b181be9edfc12e743dc1cc3715b9'}

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
                item['body'] += f'\n\nThis source-attribution presentation revision is {revision}; the original qualitative review and selected captures are unchanged.'
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
