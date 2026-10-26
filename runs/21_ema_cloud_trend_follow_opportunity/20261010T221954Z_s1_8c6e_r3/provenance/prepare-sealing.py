"""Inventory actual Stage 1 check evidence before explicit bundle preflight/sealing."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib,json,sys
stage=Path(__file__).resolve().parents[1];root=stage.parents[2]
sys.path.insert(0,str(root/'studies/21_ema_cloud_trend_follow_opportunity'))
from src.execution import assert_frozen_sources

def pin(path):
 p=stage/path
 return {'path':path,'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
assert_frozen_sources(stage,root)
required={
 'provenance/stage1-numerical.json':('passed',),
 'provenance/reviews/data-input-review.json':('passed_with_recorded_qualifications',),
 'provenance/scientific-reconciliation.json':('passed',),
 'provenance/external-bytes.json':('passed',),
 'provenance/publication-dry-run.json':('passed',),
 'provenance/reviews/report-review.json':('passed',),
 'provenance/reviews/engine-result-review.json':('passed',),
 'provenance/reviews/comparisons-uncertainty-v2-result.json':('passed',),
 'provenance/browser-review.json':('passed',),
}
for name,statuses in required.items():
 value=json.loads((stage/name).read_text());assert value.get('status') in statuses,(name,value.get('status'))
reconciliation=json.loads((stage/'data-preparation/reconciliation.json').read_text())
assert all(x['passed'] and x['unmatched_usable']==0 and not any(x['mismatch_counts'].values()) for x in reconciliation.values())
records=[
 ('check-assembly-initial-attempt','failed','provenance/check-assembly-attempt1.json'),
 ('bundle-preflight-initial-attempt','failed','provenance/bundle-preflight-attempt1.json'),
 ('study21-numerical','passed','provenance/stage1-numerical.json'),
 ('bhishma-ema-numerical','passed','provenance/stage1-numerical.json'),
 ('input-provenance','passed','provenance/reviews/data-input-review.json'),
 ('five-minute-reconciliation','passed','data-preparation/reconciliation.json'),
 ('independent-minute-aggregation','passed','data-preparation/independent-bar-aggregation-verification.json'),
 ('independent-ema-atr-initialization','passed','data-preparation/independent-feature-verification.json'),
 ('development-slice-state','passed','provenance/development-slice.json'),
 ('supplemental-slice-outcomes','passed','provenance/supplemental-verification/result.json'),
 ('full-outcome-scalar-review','passed','provenance/reviews/engine-result-review.json'),
 ('prior-ledger-byte-replay','passed','provenance/corrected-replay.json'),
 ('scientific-reconciliation','passed','provenance/scientific-reconciliation.json'),
 ('original-scientific-check','failed','provenance/scientific-original-failure.json'),
 ('coverage-verifier-fixtures','passed','provenance/reviews/coverage-fixtures.json'),
 ('full-comparison-uncertainty-reference','passed','provenance/reviews/comparisons-uncertainty-v2-result.json'),
 ('interpretation-review','passed','provenance/reviews/interpretation-review.json'),
 ('external-ledger-bytes','passed','provenance/external-bytes.json'),
 ('publication-transfer-visual-review','passed','provenance/reviews/report-review.json'),
 ('offline-browser-review','passed','provenance/browser-review.json'),
 ('publication-dry-run','passed','provenance/publication-dry-run.json'),
 ('workspace-compatibility-gate','failed','provenance/workspace-default.json'),
 ('workspace-explicit-remainder','passed','provenance/workspace-remainder.json'),
 ('workspace-tooling','passed','provenance/tooling-checks.json'),
 ('narada-initial-sandbox-checks','failed','provenance/narada-checks.json'),
 ('narada-explicit-remainder','passed','provenance/narada-remainder.json'),
 ('presentation-script-initial-attempt','failed','provenance/presentation-correction-attempt1.json'),
 ('presentation-correction-final-transfer','passed','provenance/presentation-correction.json'),
]
# The independently verified support overlay result is supplied by the lead
# after Agent A completes it; it is never inferred from an integrity pass.
coverage_result=stage/'provenance/reviews/coverage-overlay-result.json'
assert coverage_result.is_file(),'Final coverage overlay receipt required'
assert json.loads(coverage_result.read_text())['status']=='passed'
records.append(('coverage-support-overlay','passed',str(coverage_result.relative_to(stage))))
checks=[{'name':name,'status':status,'record':record} for name,status,record in records]
checks.extend([
 {'name':'original-raw-reconstruction','status':'not_run','reason':'Complete reconstruction unavailable: missing configured raw volume-rank-0 mapping, original condition JSON and ES roll-1 definition pair. Actual prerequisite test failures retained; verified published consumption is separately qualified.'},
 {'name':'native-tradingview-equivalence','status':'not_run','reason':'Native TradingView compiler/chart runtime was unavailable; independent Python scalar checks are separately recorded.'},
 {'name':'original-arrival-timing','status':'not_run','reason':'Original vendor-receipt and mapping-arrival timestamps were not retained; available_at models bar completion.'},
 {'name':'annual-exchange-calendar-certification','status':'not_run','reason':'Authoritative annual holiday/early-close certification unavailable; frozen conservative exclusions remain in force.'},
 {'name':'off-device-backup','status':'not_run','reason':'External retained research files are locally byte-verified; no independent off-device backup certification was available.'},
])
for check in checks:
 if check['status'] in ('passed','failed'):assert (stage/check['record']).is_file(),check
(stage/'provenance/checks.json').write_text(json.dumps(checks,indent=2)+'\n')
receipt={'status':'ready_to_seal','at_utc':datetime.now(timezone.utc).isoformat(),'run_id':stage.name,'source_guard':'passed','required_receipt_identities':[pin(name) for name in required],'coverage_overlay':pin(str(coverage_result.relative_to(stage))),'input_lock':pin('inputs.lock.json'),'source_inventory':pin('provenance/source-inventory.json'),'checks':pin('provenance/checks.json'),'publication':pin('publication.json'),'essential_blockers':[],'qualifications':['Input provenance passed with recorded raw reconstruction, native runtime, arrival, calendar and backup qualifications; actual retained consumption was verified.','Buy/Sell coverage is conditional on a valid cloud direction; undefined direction contributes only to All and directional coverage does not certify the whole calendar/feed.','Original full verifier failed only at the stale readiness expectation; complete independent check passed through one separately pinned coverage replacement. Frozen producer/settings/result bytes remain unchanged.','Compatibility gate retains two raw prerequisite setup errors; unaffected checks passed separately. Initial Narada loopback restriction failed, then all app gates passed with permitted loopback.','Integrity validates declared local artifacts; separate receipts verify scientific results and retained external ledger bytes. Backup/native/feed/calendar certification remains unavailable.'],'stage2_handoff':'Preserved slow baseline plus immutable same_contract_ema_cloud 1.0.0 inputs and frozen timing/state/null/width rules; no fast branch or later-period outcomes executed.'}
(stage/'provenance/sealing-review.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({'status':receipt['status'],'checks':len(checks)}))
