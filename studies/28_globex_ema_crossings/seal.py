"""Finalize saved-evidence interpretation, inventory and seal a verified fresh stage."""
from __future__ import annotations
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import html
import json
from pathlib import Path
import shutil
import sys

STUDY=Path(__file__).resolve().parent
ROOT=STUDY.parents[1]


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()


def write(path,obj):path.write_text(json.dumps(obj,indent=2,allow_nan=False)+'\n')


def require(ok,msg):
    if not ok:raise ValueError(msg)


def findings(stage):
    config=json.loads((stage/'config.json').read_text())
    require(config['primary_timeframe']=='3m' and config['timeframes']==['3m'],
            'corrected findings require the 3-minute-only configuration')
    with (stage/'tables/summary.csv').open() as f:rows=list(csv.DictReader(f))
    def value(product,segmentation='all',regime='all',cohort='common_calendar',window='globex'):
        # Explicit authored selectors avoid silently selecting another cohort.
        found=[r for r in rows if r['product']==product and r['segmentation']==segmentation and r['regime']==regime and r['cohort']==cohort and r['window']==window and r['timeframe']=='3m']
        require(len(found)==1,'summary selection must be unique');return found[0]
    overall=[value(p) for p in ['ES','NQ','GC']]
    matched=[value(p,cohort='matched_dates') for p in ['ES','NQ','GC']]
    require(len({r['sessions'] for r in matched})==1,'matched-date support differs by product')
    start,end=config['common_calendar']
    paras=[
      f'For the 6-period EMA of closing prices on 3-minute bars across the common calendar ({start}–{end}), mean full-Globex crossings per session were '+', '.join(f"{r['product']} {float(r['mean_crosses']):.2f} (n={r['sessions']})" for r in overall)+'. Corresponding medians were '+', '.join(f"{r['product']} {float(r['median_crosses']):g}" for r in overall)+'.',
      'Prior available ATR14% supplies the advance volatility classification. Low/high ATR-bin mean crossings were '+', '.join(f"{p} {float(value(p,'atr_regime','low')['mean_crosses']):.2f}/{float(value(p,'atr_regime','high')['mean_crosses']):.2f}" for p in ['ES','NQ','GC'])+'. The saved tables include support and descriptive intervals; these comparisons do not establish predictive usefulness.',
      'For the separate realized session range / prior ATR classification, quiet/active day mean crossings were '+', '.join(f"{p} {float(value(p,'realized_regime','quiet')['mean_crosses']):.2f}/{float(value(p,'realized_regime','active')['mean_crosses']):.2f}" for p in ['ES','NQ','GC'])+'. Quiet means range <0.75 ATR; active means range ≥1.25 ATR. This classification is known after the session.',
      f"There were {matched[0]['sessions']} shared eligible dates in the matched cohort. Within this cohort, quiet/active mean crossings were "+', '.join(f"{p} {float(value(p,'realized_regime','quiet','matched_dates')['mean_crosses']):.2f}/{float(value(p,'realized_regime','active','matched_dates')['mean_crosses']):.2f}" for p in ['ES','NQ','GC'])+'. Matching reduces calendar-composition differences while retaining retrospective eligibility selection.',
      'During the common 09:30–16:00 New York window, 3-minute mean crossings were '+', '.join(f"{p} {float(value(p,window='us_cash')['mean_crosses']):.2f}" for p in ['ES','NQ','GC'])+'. GC-day results use 3-minute bar opens in [08:20,13:30), beginning at 08:21; the full methodological boundary convention is retained below.',
      'Annual and monthly results are descriptive breakdowns. Common-calendar support was '+', '.join(f"{r['product']} {r['sessions']} sessions" for r in overall)+'. All saved summary rows retain support and small-cell flags. Unequal, selected coverage and partial endpoint years limit generalization and seasonality interpretations.',
      'The 3-minute bars and HLC3/volume Globex VWAP were derived for this study from the pinned one-minute source with the original published eligibility audit. This run does not claim a published 3-minute feature release. Crossing counts describe relations between two moving lines and do not establish a causal explanation, trade entry rule or profitability.',
    ]
    text='# What the sample shows\n\n'+'\n\n'.join(paras)+'\n\nEvidence: `tables/summary.csv`, selectors `timeframe=3m`, `window=globex`, `cohort=common_calendar` unless explicitly stated; `segmentation` and `regime` as named. All reported means, medians and sample sizes are taken from these saved cells.\n'
    (stage/'findings.md').write_text(text)
    report=(stage/'report.md').read_text();title,rest=report.split('\n',1)
    (stage/'report.md').write_text(title+'\n\n'+text.replace('# What the sample shows','## What the sample shows',1)+'\n'+rest)
    page=(stage/'report.html').read_text();idx=page.index('</h1>')+len('</h1>')
    block='<h2>What the sample shows</h2>'+''.join('<p>'+html.escape(p)+'</p>' for p in paras)
    (stage/'report.html').write_text(page[:idx]+block+page[idx:])


def supplementary_checks(stage):
    """Project current stage records without inventing execution or past results."""
    checks=[]
    for file in sorted((stage/'checks').glob('*.json')):
        result=json.loads(file.read_text())
        if 'exit_code' in result:
            status='not_run' if result['exit_code'] is None else ('passed' if result['exit_code']==0 else 'failed')
        else:
            status=result.get('status',result.get('outcome'))
            require(status in ['passed','failed','not_run','skipped'],
                    'check record must include actual exit_code or status: '+file.name)
        checks.append({'name':file.stem,'status':status,'record':file.relative_to(stage).as_posix()})
    if not any(r['name']=='workspace-default' for r in checks):
        checks.append({'name':'workspace-default','status':'not_run',
                       'reason':'No current-stage workspace default-gate execution record supplied; study checks do not imply a workspace pass.'})
    return checks


def main():
    p=argparse.ArgumentParser();p.add_argument('--stage',required=True,type=Path);a=p.parse_args()
    stage=a.stage.resolve()
    require(stage.parent==ROOT/'work'/STUDY.name,'explicit owned work stage required')
    dest=ROOT/'runs'/STUDY.name/stage.name
    require(not dest.exists(),'completed destination exists')
    require(not (stage/'manifest.json').exists(),'stage already finalized; inspect prior attempt')
    config=json.loads((stage/'config.json').read_text())
    require(config['protocol_version']=='1.1.0' and config['primary_timeframe']=='3m'
            and config['timeframes']==['3m'],'sealer requires corrected protocol 1.1.0 and 3-minute-only stage')
    complete=json.loads((stage/'execution-complete.json').read_text())
    require(complete['source_unchanged'] is True and complete['input_bytes_verified'] is True,'incomplete execution')
    require(complete['tests']['exit_code']==0,'numerical suite did not pass')
    scientific=json.loads((stage/'saved-evidence-verification.json').read_text())
    require(scientific['status']=='passed','scientific verification did not pass')
    require(scientific['reviewer_version']==3,'corrected 3-minute stage requires version 3 verification')
    require(scientific['bars_checked']==complete['bar_rows'] and scientific['crossings_checked']==complete['event_rows'],'verification scope differs')
    for r in scientific['artifacts']:
        require(sha(stage/r['path'])==r['sha256'],'verified numerical bytes changed: '+r['path'])
    for r in json.loads((stage/'provenance/source-inventory.json').read_text()):
        require(sha(stage/r['retained'])==r['sha256'],'retained execution source changed')
    require(sha(STUDY/'verify_saved_v3.py')==scientific['verifier_sha256'],'reviewer source changed')
    retained=stage/'provenance/finalization';retained.mkdir(parents=True,exist_ok=False)
    for source in [Path(__file__),STUDY/'verify_saved_v3.py']:
        shutil.copy2(source,retained/source.name)
    findings(stage)
    events=[{'path':r['path'],'bytes':r['bytes'],'sha256':r['sha256'],
             'locator':f"runs/{STUDY.name}/{stage.name}/{r['path']}", 'retention':'local workspace; no off-device backup asserted'}
            for r in scientific['artifacts'] if r['path'] in ['bar_evidence.parquet','crossings.csv','daily_panel.csv']]
    write(stage/'events.manifest.json',{'schema_version':1,'retention_status':'local retained; large files Git-ignored','artifacts':events,'bar_rows':complete['bar_rows'],'crossing_rows':complete['event_rows'],'daily_panel_rows':complete['daily_panel_rows']})
    execution=json.loads((stage/'provenance/execution.json').read_text())
    command_records=[{'argv':execution['argv'],'cwd':execution['cwd'],'environment':{'UV_CACHE_DIR':'/private/tmp/abacus-study28-uv-cache'}},
      {'argv':json.loads((stage/'figure-environment.json').read_text())['argv'],'cwd':str(ROOT)},
      {'argv':scientific['execution']['argv'],'cwd':scientific['execution']['cwd']},
      {'argv':[sys.executable,*sys.argv],'cwd':str(ROOT)},
      {'argv':complete['tests']['argv'],'cwd':str(ROOT)}]
    # The presentation receipt retains Python executable separately from script argv.
    command_records[1]['argv']=[json.loads((stage/'figure-environment.json').read_text())['executable'],*command_records[1]['argv']]
    write(stage/'commands.json',command_records)
    checks=[{'name':'owned-numerical-suite','status':'passed','record':'execution-complete.json'},
            {'name':'independent-saved-evidence','status':'passed','record':'saved-evidence-verification.json'},
            {'name':'pinned-input-bytes','status':'passed','record':'input-verification.json'}]
    checks.extend(supplementary_checks(stage))
    write(stage/'checks.json',checks)
    visual_record=stage/'checks/visual-inspection.json'
    write(stage/'finalization.json',{'prepared_utc':datetime.now(timezone.utc).isoformat(),
      'destination':dest.relative_to(ROOT).as_posix(),'numerical_evidence_unchanged':True,
      'interpretation':'Authored from exact saved summary cells in retained seal.py before sealing; no numerical recalculation.',
      'workspace_verification':'Current-stage executed or unexecuted scope is recorded in checks.json; prior-run workspace results are not current-run passes.',
      'prior_run_invariants':({'record':'saved-evidence-verification.json','field':'previous_run_invariants'}
                              if 'previous_run_invariants' in scientific else None),
      'visual_check':({'record':visual_record.relative_to(stage).as_posix()}
                      if visual_record.is_file() else {'status':'not_run','reason':'No current-stage visual inspection record supplied.'}),
      'publication':'Local offline research bundle; no Narada or public hosting.'})
    all_artifacts=[{'path':f.relative_to(stage).as_posix(),'bytes':f.stat().st_size,'sha256':sha(f)}
                   for f in sorted(stage.rglob('*')) if f.is_file()]
    sourcepaths=[r['retained'] for r in json.loads((stage/'provenance/source-inventory.json').read_text())]
    sourcepaths.extend([p.relative_to(stage).as_posix() for p in retained.glob('*.py')])
    manifest={'contract':'abacus.evidence/v1','bundle_kind':'research','study_id':STUDY.name,'run_id':stage.name,
      'inventory_scope':'declared_artifacts','results':{'kind':'quantitative','state':'computed','artifacts':['metrics.json','tables/summary.csv','report.md','findings.md']},
      'provenance':{'settings':'config.json','input_lock':'inputs.lock.json','exclusions':'input_audit.csv',
        'commands':'commands.json','checks':'checks.json','environment_lock':'provenance/source/uv.lock',
        'code':{'revision':execution['git_revision'],'dirty':execution['dirty'],'status':'provenance/git-status.txt',
          'source_snapshot':{'paths':sourcepaths,'scope':'Declared study producers/tests/docs, Bhishma package sources and exact separate verification/finalization scripts. Not dependency closure.'}}},
      'artifacts':all_artifacts}
    write(stage/'manifest.json',manifest)
    sys.path.insert(0,str(ROOT/'scripts'))
    from evidence_contract import assess_bundle
    assessed=assess_bundle(stage)
    require(assessed['status']=='verified_declared_artifacts','integrity assessment failed: '+json.dumps(assessed))
    dest.parent.mkdir(parents=True,exist_ok=True)
    stage.rename(dest)
    print(json.dumps({'status':'sealed','path':str(dest),'artifacts':len(all_artifacts)},indent=2))


if __name__=='__main__':main()
