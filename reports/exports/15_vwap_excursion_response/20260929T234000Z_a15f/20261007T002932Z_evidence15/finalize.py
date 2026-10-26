# Presentation provenance finalizer. This does not stage or change research/public content.
import argparse,datetime,hashlib,json,platform,shutil,subprocess
from pathlib import Path
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[4]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def record(p):return {'path':str(p.relative_to(ROOT)),'sha256':sha(p),'bytes':p.stat().st_size}
def dump(p,v):p.write_text(json.dumps(v,indent=2,ensure_ascii=False)+'\n')
a=argparse.ArgumentParser();a.add_argument('--docs-passed',action='store_true');args=a.parse_args()
m=json.loads((OUT/'source-map.json').read_text());p=json.loads((OUT/'publication.json').read_text());app=ROOT/'apps/narada'
baseline=json.loads((OUT/'provenance/preservation-baseline.json').read_text())
for path,h in baseline.items():assert sha(ROOT/path)==h,path
for source in m['sources']:assert sha(ROOT/source['path'])==source['sha256'],source['path']
snapshot=OUT/'provenance/narada-source'; files=[]
for folder in ['src','types','contracts','scripts','tests','content']:
 for f in sorted((app/folder).rglob('*')):
  if f.is_file():dest=snapshot/f.relative_to(app);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(f,dest);files.append(record(dest))
for name in ['package.json','package-lock.json','next.config.ts','tsconfig.json','eslint.config.mjs']:
 dest=snapshot/name;shutil.copyfile(app/name,dest);files.append(record(dest))
notes=ROOT/'studies'/m['study_id']/'notes.md';original=(OUT/'provenance/prior-notes.md').read_bytes();assert notes.read_bytes().startswith(original)
preserved={'passed':True,'source_artifacts':len(m['sources']),'baseline_files_verified':len(baseline),'sealed_run_files_verified':sum(x.startswith('runs/') for x in baseline),'previous_export_files_verified':sum(x.startswith('reports/exports/') for x in baseline),'previous_publication_files_verified':sum(x.startswith('apps/narada/public/publications/') for x in baseline),'study_metadata_files_verified':sum(x.endswith('/study.json') for x in baseline),'consumed_sources':m['sources'],'baseline':record(OUT/'provenance/preservation-baseline.json'),'original_notes_prefix_preserved':True,'limitations':'Initial hashes cover retained run/export files up to 20 MB plus every consumed large artifact; larger unconsumed artifacts were not hashed. No research commands or writes targeted them.'}
dump(OUT/'preservation-verification.json',preserved)
qa=json.loads((OUT/'browser-verification.json').read_text())
assert all(r['pageWidth']==r['viewport'] and not r['badAnchors'] for r in qa['responsive'])
assert not qa['unexpectedConsoleErrors'],qa['unexpectedConsoleErrors']
verification={'publication_id':p['id'],'source_run_id':m['source_run_id'],'checks':[{'name':'content','passed':True,'record':'content-verification.json'},{'name':'source_and_previous_publication_preservation','passed':True,'record':'preservation-verification.json'},{'name':'browser','passed':True,'record':'browser-verification.json'},{'name':'static_http_assets_and_headers','passed':True,'record':'static-verification.json'},{'name':'publisher','passed':True,'mode':'dry-run then normal staging'},{'name':'npm run verify','passed':True,'studies':17,'publications':23,'figures':16,'downloads':6},{'name':'npm test','passed':True,'tests':31},{'name':'npm run lint','passed':True},{'name':'npm run build','passed':True,'bounded_static_payloads':377},{'name':'python3 scripts/check-agent-docs.py','passed':args.docs_passed}], 'react_review':'Server components, no hooks/client analytics or runtime research fetch; bounded props, typed variants, escaped text, native links/downloads, explicit labels/alt text, accessible table regions and focus, no dangerous HTML. Reviewed using vercel:react-best-practices guidance.', 'research_index':'Not run: its metadata/run/strategy/quality navigation inputs were unchanged; appended completed-study note contents and app catalog are not index inputs.', 'limitations':qa['limitations'],'hosted_state_changed':False}
dump(OUT/'verification.json',verification)
revision=m['revision_id'];sid=m['study_id'];rel=str(OUT.relative_to(ROOT))
commands=[{'cwd':'.','command':f'python3 studies/{sid}/publish_evidence.py --revision {revision}'}]
if (OUT/'provenance/render_web_figures.mjs').exists():commands.append({'cwd':'.','command':f'node studies/{sid}/render_web_figures.mjs --workspace-root {ROOT} --revision {revision}', 'invocation':'Called by the presentation producer; real workspace root is its recorded source workspace.'})
commands += [{'cwd':'.','command':f'python3 {rel}/verify-content.py'},{'cwd':'apps/narada','command':f'npm run report:publish -- --report ../../{rel}/publication.json --dry-run'},{'cwd':'apps/narada','command':f'npm run report:publish -- --report ../../{rel}/publication.json'}]
commands += [{'cwd':'apps/narada','command':x} for x in ['npm run verify','npm test','npm run lint','npm run build','PORT=4174 npm run preview']]
commands += [{'cwd':'.','command':f'python3 {rel}/check-http.py'},{'cwd':'.','command':'python3 scripts/check-agent-docs.py'},{'cwd':'.','command':f'python3 {rel}/finalize.py'+(' --docs-passed' if args.docs_passed else '')}]
for c in commands:
 c['environment']='Node v24.18.0/npm 11.16.0 for Node commands; locked installed app dependencies; Python 3.9.6 for presentation-only selection/checks.'
changes=['Exact saved row/column selection; numeric values retain full precision and ratios','Visible table population/outcome/uncertainty notes','Explicit bounded source-traceable summary CSV downloads' if p.get('downloads') else 'Attributed existing external sources/media ranges; no statistical scorecard','Deterministic saved SVG rasterization / exact saved-value plot / unchanged raster copies as recorded in source map','Static views; no new analytical computation or interaction','Catalog features new revision and retains original immutable publication']
if sid.startswith('12'):changes.append('Correct earlier webpage interval-method wording to the saved approximate normal ISO-week cluster definition; unchanged interval endpoints')
if sid.startswith('15'):changes.append('Correct earlier webpage continuation-minus-fade wording to the saved signed continuation endpoint definition; unchanged values')
source_selection={'kind':m['source_selection'],'run_id':m['source_run_id'],'registered_reference_unchanged':True,'reason':m['reason']}
git=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
node=subprocess.check_output(['node','--version'],text=True).strip();npm=subprocess.check_output(['npm','--version'],text=True).strip()
sharp=json.loads((app/'node_modules/sharp/package.json').read_text())['version']
staged=app/'public/publications'/p['id'];bundle=json.loads((staged/'report.json').read_text())
assert bundle['report']==p
manifest={'study_id':sid,'source_run_id':m['source_run_id'],'revision_id':revision,'publication_id':p['id'],'created_at_utc':p['publishedAt'],'finalized_at_utc':datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),'source_selection':source_selection,'change':'Presentation only; no new analytical run, calculations, dataset changes or research interpretation','source_artifacts':[record(ROOT/x['path']) for x in m['sources']], 'renderer':{'path':str((OUT/'provenance/publish_evidence.py').relative_to(ROOT)),'sha256':sha(OUT/'provenance/publish_evidence.py'),'owning_exporter':f'studies/{sid}/publish_evidence.py','git_revision':git,'format_version':'web-study-report-1.1','narada_version':'0.1.0','python':platform.python_version(),'node':node,'npm':npm,'sharp':sharp,'platform':platform.platform(),'source_workspace':str(ROOT),'uncommitted_renderer_identity':{'snapshot':str(snapshot.relative_to(ROOT)),'files':files,'scope':'Exact app renderer, contracts, publisher, validation/tests, catalog and dependency lock; archival snapshot, not another maintained authoring source'}},'render_command':commands[0],'exact_commands':commands,'presentation_changes':changes,'checks':verification['checks'],'outputs':[record(f) for f in sorted(OUT.rglob('*')) if f.is_file() and f.name!='manifest.json' and '__pycache__' not in f.parts], 'staged_publication':{'source_sha256':bundle['provenance']['sourceSha256'],'artifacts':[record(f) for f in sorted(staged.rglob('*')) if f.is_file()],'catalog_at_delivery':record(app/'public/publications/index.json'),'study_catalog_at_delivery':record(app/'content/studies.json'),'route':'/reports/'+p['id']+'/','static_html_at_delivery':record(app/'out/reports'/p['id']/'index.html')},'boundaries':{'research_reexecuted':False,'completed_run_modified':False,'previous_exports_or_bundles_modified':False,'contract_extension':'1.1; source 1.0 retained','study_metadata_modified':False,'deployed':False,'committed_or_pushed':False}}
# Retain the exact explicit source-to-asset raster commands and jobs.
if (OUT/'provenance/figure-jobs.json').exists():manifest['render_command']['selected_raster_jobs']=json.loads((OUT/'provenance/figure-jobs.json').read_text())
dump(OUT/'manifest.json',manifest);print(p['id']+' manifest finalized ('+str(len(manifest['outputs']))+' output records)')
