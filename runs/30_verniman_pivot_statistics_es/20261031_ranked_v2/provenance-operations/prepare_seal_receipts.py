"""Retain observed local checks and failed attempts before sealing v2."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[3]
OPS = Path(__file__).resolve().parent
STAGE = ROOT / 'work/30_verniman_pivot_statistics_es/20261031_ranked_v2'
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
required = ['freeze-v2','audit-v2','execute-v2','render-v2','parity-v2','verify-v2','publish-v2',
            'diagnostic-reconciliation-v2','owning-study-harness-v2','period-coverage-v2',
            'dry-run-pivot-v2','dry-run-vwap-v2','publish-pivot-v2','publish-vwap-v2',
            'narada-verify-v2','narada-tests-v2','narada-lint-v2','narada-build-v2',
            'narada-source-audit-existing-v2','narada-http-preview-v2','tooling-metadata-r2','workspace-unaffected']
checks = []
for name in required:
    path = OPS / 'checks' / (name+'.json')
    record = json.loads(path.read_text())
    if record.get('status') != 'passed' or record.get('exit_code') != 0:
        raise ValueError('Required check not actually successful: '+name)
    log = path.with_suffix('.log')
    if record.get('log_sha256') and sha(log) != record['log_sha256']:
        raise ValueError('Check log changed: '+name)
    checks.append({'name':name,'passed':True,'record':f'provenance-operations/checks/{path.name}',
                   'record_sha256':sha(path),'log_sha256':sha(log)})
protected = json.loads((OPS/'preserved-baseline-files.json').read_text())
for row in protected:
    if sha(ROOT/row['path']) != row['sha256']:
        raise ValueError('Protected baseline changed: '+row['path'])
download = json.loads((OPS/'native-download-verification.json').read_text())
if download['status'] != 'passed' or download['sha256'] != download['expected_sha256']:
    raise ValueError('Native CSV byte check did not pass')
browser = {'status':'passed','created_at':datetime.now(timezone.utc).isoformat(),
    'origin':'http://127.0.0.1:4173','browser':'ChatGPT in-app browser',
    'desktop':{'viewport':[1440,1000],'document_width':1440,'table_client_width':916,'table_scroll_width':1400,
               'keyboard_scroll_left_before':0,'keyboard_scroll_left_after':40},
    'mobile':{'viewport':[390,844],'document_width':390,'table_client_width':350,'table_scroll_width':1400,
              'keyboard_scroll_left_before':0,'keyboard_scroll_left_after':40},
    'checks':[
        'Explore lists two Ranked statistics views and six Original baseline views.',
        'Pivot report first-cross timing controls load saved rows; All selections show242 rows on three100-row pages.',
        'Next rows visibly shows page2, rows101–200.',
        'Opening selected-row URL shows pending selection and authored defaults; explicit loading restores all242 rows.',
        'Recent last20 timing selection shows one saved row,15 valid event days and5 missing/no-cross days.',
        'Mobile VWAP population switch changes saved full-Globex denominator1292 to RTH denominator1308.',
        'Mobile native contents disclosure expands and its first-cross link navigates to#section-s12.',
        'Original baseline opens the retained20261031_repo_v2 report and exposes all six report links.',
        'No console warnings/errors captured during the tested navigation.',
        'Viewport override reset; Explore left open as a deliverable.'
    ],
    'native_download':download,
    'bounded_operations':'UI actions10–15seconds; native download/event/path waits15seconds.',
    'recovered_attempt':'The mobile Contents disclosure is a native summary; a button-role locator matched none. DOM inspection identified summary, whose actual expansion and section-link navigation passed.',
    'limits':'Manual interaction observations; no native print/PDF pagination or hosted deployment test.'}
(OPS/'browser-verification.json').write_text(json.dumps(browser,indent=2)+'\n')
retained=STAGE/'provenance-operations'
retained.mkdir(exist_ok=False)
shutil.copytree(OPS/'checks',retained/'checks')
for path in OPS.iterdir():
    if path.is_file() and path.suffix in ('.py','.json','.csv'):
        shutil.copyfile(path,retained/path.name)
diagnostic=ROOT/'work/30_verniman_pivot_statistics_es/20261031_ranked_v1_checker_diagnostic_v2'
(retained/'checker-diagnostic').mkdir()
for path in diagnostic.iterdir():
    if path.is_file() and path.suffix in ('.json','.log','.py'):
        shutil.copyfile(path,retained/'checker-diagnostic'/path.name)
old=ROOT/'work/30_verniman_pivot_statistics_es/20261031_ranked_v1'
pins=[old/name for name in ('freeze.json','execution.json','ranked-execution.json','ledgers.json.gz','ranked-ledgers.json.gz','tables/ranked_summary.csv')]
old_manifest={'status':'unsealed_failed_diagnostic_retained','artifacts':[{'path':str(p.relative_to(ROOT)),'sha256':sha(p),'bytes':p.stat().st_size} for p in pins],
    'qualification':'Retained local diagnostic, not selected completed evidence. No off-device backup asserted.'}
(STAGE/'diagnostics.manifest.json').write_text(json.dumps(old_manifest,indent=2)+'\n')
local={'status':'passed','scope':'Required study and local publication gates only; compatibility default is separately failed below.',
       'created_at':datetime.now(timezone.utc).isoformat(),'checks':checks,
       'browser_verification':{'path':'provenance-operations/browser-verification.json','sha256':sha(retained/'browser-verification.json')},
       'protected_baseline_files_unchanged':len(protected),
       'compatibility_default':{'status':'failed','exit_code':1,'record':'provenance-operations/checks/workspace-default.json',
           'reason':'Two pre-existing Bhishma configured-input prerequisites missing: original volume-lead mapping JSON and ES roll-1 point-in-time definition pair. Later unaffected checks passed separately.'},
       'source_audit_scope':'Preseal audit covers103 existing mapped publications; new2 source cells/assets and period downloads verified separately. Full105 source mapping audit is required after sealing and must be recorded separately.',
       'publication_transfer':{'saved_cells':51576,'raster_assets':8},
       'http_preview':{'pages':231,'exported_files':234,'real_404s':6,'requests':480},
       'qualifications':['Bootstrap intervals not independently re-estimated.','Historical pivot availability and original vendor/native-chart parity remain unverified.','No fills, costs, profitability or hosted deployment tested.']}
with (STAGE/'local-verification.json').open('x') as stream:json.dump(local,stream,indent=2);stream.write('\n')
print(json.dumps({'status':'passed','required_exit_bound_checks':len(checks),'protected_files':len(protected),'native_download_bytes':download['bytes']}))
