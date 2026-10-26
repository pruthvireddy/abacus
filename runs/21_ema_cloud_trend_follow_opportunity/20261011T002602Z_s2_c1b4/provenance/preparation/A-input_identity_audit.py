from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,stat
root=Path('.').resolve();base=root/'runs/21_ema_cloud_trend_follow_opportunity/20261010T221954Z_s1_8c6e_r3'
started=datetime.now(timezone.utc).isoformat()
def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(8<<20),b''):h.update(b)
 return h.hexdigest()
def safe(p,within):
 p=Path(p)
 if not p.is_absolute():p=within/p
 if not p.resolve().is_relative_to(within):raise ValueError('outside scoped root '+str(p))
 cur=p
 while cur!=within:
  if cur.is_symlink():raise ValueError('symlink '+str(cur))
  cur=cur.parent
 if not stat.S_ISREG(p.stat().st_mode):raise ValueError('nonregular '+str(p))
 return p
mismatches=[];counts={};observed={}
def verify(records,scope,name,pathkey='path'):
 count=0
 for r in records:
  p=safe(r[pathkey],scope);actual=digest(p);size=p.stat().st_size
  if actual!=r['sha256'] or ('bytes' in r and size!=r['bytes']):mismatches.append({'check':name,'path':str(p),'expected':r['sha256'],'actual':actual})
  observed[str(p)]={'sha256':actual,'bytes':size};count+=1
 counts[name]=count
 return count
hand=json.loads((base/'stage2-handoff.json').read_text());manifest=json.loads((base/'manifest.json').read_text());lock=json.loads((base/'inputs.lock.json').read_text());ledgers=json.loads((base/'events.manifest.json').read_text());sources=json.loads((base/'provenance/source-inventory.json').read_text())
verify(hand['slow_baseline'],base,'handoff_baseline',pathkey='artifact')
verify(manifest['artifacts'],base,'sealed_local_artifacts')
verify(manifest['external_artifacts'],root,'sealed_external_ledgers',pathkey='locator')
verify(ledgers['records'],root,'ledger_manifest_records')
verify([{'path':r['snapshot_path'],'sha256':r['sha256'],'bytes':r['bytes']} for r in sources['sources']],base,'frozen_sources')
delivery=safe(hand['reusable_delivery']['manifest'],root)
verify([{'path':str(delivery),'sha256':hand['reusable_delivery']['sha256']}],root,'reusable_delivery_manifest')
release=json.loads(delivery.read_text())
verify(release['output_files'],root,'reusable_delivery_partitions')
verify(release['auxiliary_files'],root,'reusable_delivery_auxiliary')
verify(lock['input_manifests'],root,'market_manifest_pins')
verify([r for r in lock['files'] if r['role']!='executed_data_source'],root,'consumed_market_support_and_environment')
resolved=[]
for r in lock['files']:
 if r['role']=='executed_data_source':
  retained=root/'data/features/ema_cloud/version=1.0.0/provenance'/Path(r['path']).name
  verify([dict(r,path=str(retained))],root,'historical_source_'+retained.name)
  canonical=safe(r['path'],root);actual=digest(canonical)
  resolved.append({'historical_canonical_locator':r['path'],'historical_sha256':r['sha256'],'resolved_retained_snapshot':str(retained),'current_canonical_sha256':actual,'current_differs_from_historical_producer':actual!=r['sha256']})
current_changes=[]
for r in sources['sources']:
 path=safe(r['workspace_path'],root);actual=digest(path)
 if actual!=r['sha256']:current_changes.append({'path':r['workspace_path'],'frozen_sha256':r['sha256'],'current_sha256':actual})
receipt={'status':'passed' if not mismatches else 'failed','started_at':started,'completed_at':datetime.now(timezone.utc).isoformat(),'checks':counts,'mismatches':mismatches,'baseline_manifest_sha256':digest(base/'manifest.json'),'handoff_sha256':digest(base/'stage2-handoff.json'),'delivery_manifest_sha256':digest(delivery),'current_vs_frozen_sources':current_changes,'historical_producer_resolutions':resolved,'unique_verified_paths':len(observed),'outcomes_computed':False,'features_rebuilt':False,'interpretation':'Declared-byte identity audit only; baseline scientific validity derives from retained independent receipts. Historical producer snapshot differs intentionally from corrected canonical EMA source; later verifier/caption repairs are distinguished from frozen executed bytes.'}
print(json.dumps(receipt,indent=2))
