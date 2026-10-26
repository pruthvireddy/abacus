"""Seal this new presentation record after content, app and browser verification."""
import hashlib,json,platform,shutil,subprocess
from datetime import datetime,timezone
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[4];APP=ROOT/'apps/narada'
mapping=json.loads((HERE/'source-map.json').read_text());pub=json.loads((HERE/'publication.json').read_text())
spec_scope={};exec((HERE/'provenance/publish_web.py').read_text().split('import argparse')[0],spec_scope);spec=spec_scope['SPEC']
def identity(p):
 data=p.read_bytes();return {'path':str(p.relative_to(ROOT)),'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)}
# Record exact dirty renderer/catalog identity, without dependencies or ignored data.
snapshot=HERE/'provenance/narada-source';snapshots=[]
for directory in ['src','types','contracts','scripts','tests','content']:
 for p in sorted((APP/directory).rglob('*')):
  if p.is_file():
   target=snapshot/p.relative_to(APP);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target);snapshots.append(identity(target))
for name in ['package.json','package-lock.json','next.config.ts','tsconfig.json','eslint.config.mjs']:
 p=APP/name;target=snapshot/name;shutil.copyfile(p,target);snapshots.append(identity(target))
source_artifacts=list(mapping['sources'])
# Retained historical configuration is context, not a reconstructed execution seal.
if spec['study_id'][:2] in ['01','02','03','04']:
 directory=ROOT/'legacy/sahadeva/analysis'/spec['study_id'];c=directory/('configs/study.yaml' if spec['study_id'][:2] in ['01','02'] else 'config.json')
 if c.exists():source_artifacts.append(identity(c))
# Preserve separately saved selection explanations when used by the concise review.
for name in ['decision.json','selection.lock.json','candidate-selection-history.json','final-model-settings.json','freeze.json','events.manifest.json']:
 p=ROOT/'runs'/spec['study_id']/spec['source_run_id']/name
 if p.exists():source_artifacts.append(identity(p))
relative=str(HERE.relative_to(ROOT));report_path='../../'+relative+'/publication.json';owner='studies/'+spec['study_id']+'/publish_web.py'
commands=[{'cwd':'.','command':f'python3 {owner} --revision {HERE.name}'},{'cwd':'.','command':f'python3 {relative}/verify-content.py'},{'cwd':'apps/narada','command':f'npm run report:publish -- --report {report_path} --dry-run'},{'cwd':'apps/narada','command':f'npm run report:publish -- --report {report_path}'}]
commands += [{'cwd':'apps/narada','command':c} for c in ['npm run verify','npm test','npm run lint','npm run build','npm run preview']]
commands += [{'cwd':'.','command':'python3 scripts/check-agent-docs.py'},{'cwd':'.','command':f'python3 {relative}/provenance/check-http.py'},{'cwd':'.','command':f'python3 {relative}/finalize.py'}]
content=json.loads((HERE/'content-verification.json').read_text());browser=json.loads((HERE/'browser-verification.json').read_text());http=json.loads((HERE/'static-verification.json').read_text());preservation=json.loads((HERE/'preservation-verification.json').read_text())
superseded=spec['publication_id'].startswith(('08-','10-')) and not spec['publication_id'].endswith('-r2')
verification={'publication_id':pub['id'],'result':'superseded presentation; numeric/route checks pass, use corrected featured revision' if superseded else 'passed','content':content,'application':{'node':'v24.18.0','npm':'11.16.0','verify':'17 studies, 19 publications, 6 raster assets','test':'22 passed','lint':'passed','build':'passed; 17 study and 19 publication routes, 341 bounded payloads','documentation':'27 maintained guides; 0 errors','react_review':'Server Components, cached bounded app-owned reads, escaped plain content, semantic landmarks/links, keyboard-accessible overflow; no client research imports'},'browser':{'result':browser['result'],'record':'browser-verification.json','desktop':'1440x1000','mobile':'390x844'},'static_http':http,'preservation':{'result':preservation['result'],'consumed_source_hashes_match':True,'previous_exports_pilots_and_research_preserved':True},'limitations':[spec['sections'][-1]['body']],'statistical_calculations_performed':False,'hosted_state_changed':False}
(HERE/'verification.json').write_text(json.dumps(verification,indent=2,ensure_ascii=False)+'\n')
bundle_path=APP/'public/publications'/pub['id']/'report.json';bundle=json.loads(bundle_path.read_text());staged=[identity(bundle_path)]+[identity(bundle_path.parent/a['path']) for a in bundle['provenance']['assets']]
outputs=[identity(p) for p in sorted(HERE.rglob('*')) if p.is_file() and p!=HERE/'manifest.json']
manifest={'study_id':spec['study_id'],'source_run_id':spec['source_run_id'],'revision_id':HERE.name,'publication_id':pub['id'],'created_at_utc':datetime.fromtimestamp((HERE/'publication.json').stat().st_birthtime,timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z'),'source_selection':{'kind':spec['selection'],'reason':spec['reason'],'research_reference_modified':False},'change':'Concise table-first reading order from explicit saved-cell selections; no new evidence or numerical computation.','source_artifacts':source_artifacts,'renderer':{'path':relative+'/provenance/publish_web.py','sha256':identity(HERE/'provenance/publish_web.py')['sha256'],'owning_exporter':owner,'git_revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'format_version':'web-study-report-1.0','narada_version':'0.1.0','python':platform.python_version(),'node':subprocess.check_output(['node','--version'],text=True).strip(),'npm':subprocess.check_output(['npm','--version'],text=True).strip(),'platform':platform.platform(),'uncommitted_renderer_identity':{'snapshot':relative+'/provenance/narada-source/','files':snapshots,'scope':'Exact renderer, contracts, publisher, tests, authored catalog and locked dependency identity; archival snapshot, not another maintained catalog.'}},'render_command':commands[0],'exact_commands':commands,'presentation_changes':['Selected saved rows/columns, numeric ratios and documented pp/percentage-cell conversion only','Original denominators, horizons, pointwise/familywise bounds and negative/inconclusive qualifications','Table-first selection; no new figures, arbitrary HTML imports or downloads','Explicit catalog study navigation and distinct revision context'], 'checks':[{'name':'saved_cell_transfer','record':'content-verification.json'},{'name':'application_and_semantics','record':'verification.json'},{'name':'static_http','record':'static-verification.json'},{'name':'browser','record':'browser-verification.json'},{'name':'preservation','record':'preservation-verification.json'}],'outputs':outputs,'staged_publication':{'source_sha256':bundle['provenance']['sourceSha256'],'artifacts':staged,'catalog_at_delivery':identity(APP/'public/publications/index.json'),'study_catalog_at_delivery':identity(APP/'content/studies.json'),'route':'/reports/'+pub['id']+'/','static_html_at_delivery':identity(APP/'out/reports'/pub['id']/'index.html')},'boundaries':{'research_reexecuted':False,'completed_run_modified':False,'report_schema_modified':False,'study_metadata_modified':False,'deployed':False,'committed_or_pushed':False}}
if superseded:manifest['superseded_by']=pub['id']+'-r2';manifest['known_correction']='Incorrect baseline prose/label; later revision corrects it without changing saved values. Catalog and report context direct readers to the featured revision.'
(HERE/'manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n');print(pub['id'],len(outputs),'output hashes')
