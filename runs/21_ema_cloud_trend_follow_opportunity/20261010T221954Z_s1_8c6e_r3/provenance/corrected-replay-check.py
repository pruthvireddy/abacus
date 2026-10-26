"""Byte-only comparison with preserved diagnostic execution; no calculations."""
from pathlib import Path
from datetime import datetime, timezone
import json, hashlib
stage=Path(__file__).resolve().parent.parent
workspace=Path.cwd()
old=workspace/'work/21_ema_cloud_trend_follow_opportunity/20261010T220715Z_s1_8c6e_r2'
def pin(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return {'path':str(p),'bytes':p.stat().st_size,'sha256':h.hexdigest()}
def verify(r):
    p=Path(r['path']);x=pin(p)
    if (x['bytes'],x['sha256'])!=(r['bytes'],r['sha256']):raise ValueError('ledger byte mismatch '+str(p))
    return x
prior=json.loads((old/'events.manifest.json').read_text())['records']
current=json.loads((stage/'events.manifest.json').read_text())['records']
key=lambda r:(r['product'],r['interval_minutes'],r['role'])
a={key(r):r for r in prior};b={key(r):r for r in current}
if a.keys()!=b.keys() or len(a)!=24:raise ValueError('ledger roster mismatch')
checks=[]
for k in sorted(a):
    verify(a[k]);verify(b[k])
    if any(a[k][f]!=b[k][f] for f in ['bytes','sha256','row_count','schema']):raise ValueError('replay changed saved ledger '+str(k))
    checks.append({'product':k[0],'interval_minutes':k[1],'role':k[2],'prior':pin(Path(a[k]['path'])),'current':pin(Path(b[k]['path'])),'row_count':b[k]['row_count'],'identical':True})
oldsrc=json.loads((old/'provenance/source-inventory.json').read_text())['sources']
newsrc=json.loads((stage/'provenance/source-inventory.json').read_text())['sources']
a={r['workspace_path']:r for r in oldsrc};b={r['workspace_path']:r for r in newsrc}
if a.keys()!=b.keys():raise ValueError('source roster changed')
changes=[{'path':p,'prior_sha256':a[p]['sha256'],'current_sha256':b[p]['sha256']} for p in a if a[p]['sha256']!=b[p]['sha256']]
allowed={f'studies/21_ema_cloud_trend_follow_opportunity/{p}' for p in ['src/statistics.py','src/reconcile.py','tests/test_statistics.py','tests/test_reconcile.py','protocol-stage1.md','config-stage1.json']}
if {r['path'] for r in changes}!=allowed:raise ValueError('unexpected source changes '+str(changes))
result={'status':'passed','recorded_at_utc':datetime.now(timezone.utc).isoformat(),'checker':pin(Path(__file__)),'prior_run_id':old.name,'current_run_id':stage.name,'ledger_comparisons':checks,'source_changes':changes,'scope':'All24 bars/technical/event/outcome ledgers identical bytes and schemas; scientific signal/path rules unchanged. Calendar/stats and independent verifier correction plus fixtures/protocol only. Does not certify the obsolete bootstrap or backup retention.'}
(stage/'provenance/corrected-replay.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'status':'passed','identical_ledgers':24,'expected_source_changes':len(changes)}))
