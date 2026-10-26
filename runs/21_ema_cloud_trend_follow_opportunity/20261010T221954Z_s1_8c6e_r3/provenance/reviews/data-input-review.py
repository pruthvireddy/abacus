"""Read-only final consumed-input reviewer; computes no signals or outcomes."""
from datetime import datetime,timezone
from pathlib import Path
import json
import sys
from collections import Counter
import numpy as np
import pandas as pd
from abacus_bhishma.paths import load_workspace_paths
from abacus_bhishma.provenance import sha256_file
from abacus_bhishma.ema_cloud import load_release

root=Path.cwd();stage=Path(__file__).resolve().parents[2]
paths=load_workspace_paths(root);pub=paths.publication_root
lock_path=stage/'inputs.lock.json';lock=json.loads(lock_path.read_text())
receipt_path=Path(__file__).with_suffix('.json')
if receipt_path.exists():raise FileExistsError('fresh reviewer receipt required')
verified=[];historical=[];blockers=[]
def verify(record,base):
    path=base/record['path'];actual=sha256_file(path)
    if actual!=record['sha256'] or ('bytes' in record and path.stat().st_size!=record['bytes']):
        raise ValueError('pinned bytes mismatch: '+str(path))
    return dict(path=str(path),sha256=actual,bytes=path.stat().st_size)

correction=json.loads((stage/'data-preparation/source-correction.json').read_text())
for r in lock['input_manifests']+[lock['delivery'],lock['semantic_reference']]:
    verified.append(verify(r,pub))
for r in lock['files']:
    if r['role']=='executed_data_source':
        current=pub/r['path'];retained=pub/'data/features/ema_cloud/version=1.0.0/provenance'/current.name
        resolved=dict(path=str(retained.relative_to(pub)),bytes=r['bytes'],sha256=r['sha256'])
        historic=verify(resolved,pub)
        canonical_sha=sha256_file(current)
        if canonical_sha!=r['sha256']:
            if current.name!='ema_cloud.py' or canonical_sha!=correction['corrected_canonical']['sha256']:
                raise ValueError('unqualified historical producer mismatch')
            historic.update(recorded_original_canonical_locator=r['path'],current_canonical_sha256=canonical_sha,
                resolution='Preserved immutable producer snapshot; explicit source-correction companion. Current study code is separately frozen.')
        historical.append(historic)
    else:verified.append(verify(r,pub))
manifest_path=pub/lock['delivery']['path'];manifest=json.loads(manifest_path.read_text())
for r in manifest['output_files']+manifest['auxiliary_files']:
    verified.append(verify(r,pub))
# Validate actual current study loader/source identities against r2 freeze.
inventory_path=stage/'provenance/source-inventory.json';inventory=json.loads(inventory_path.read_text())
frozen_count=0
for r in inventory['sources']:
    if r['workspace_path'].startswith('packages/bhishma/src/abacus_bhishma/'):
        verify(dict(path=r['workspace_path'],sha256=r['sha256'],bytes=r['bytes']),root)
        verify(dict(path=r['snapshot_path'],sha256=r['sha256'],bytes=r['bytes']),stage)
        frozen_count+=1
coverage_path=stage/'data-preparation/decision-coverage.csv'
coverage=pd.read_csv(coverage_path);computed=[];rosters=[]
endpoint=pd.Timestamp('2021-01-01',tz='America/New_York').tz_convert('UTC')
for product in ('ES','GC','NQ'):
    five=load_release(pub,product=product,interval=5,manifest_path=lock['delivery']['path'],expected_manifest_sha256=lock['delivery']['sha256'])
    for interval in (3,5):
        bars=five if interval==5 else load_release(pub,product=product,interval=3,manifest_path=lock['delivery']['path'],expected_manifest_sha256=lock['delivery']['sha256'])
        if bars.timestamp.duplicated().any() or not bars.timestamp.is_monotonic_increasing:raise ValueError('invalid roster identity')
        if not bars.available_at.le(endpoint).all():raise ValueError('delivery beyond approved endpoint')
        if not bars.loc[bars.usable,'contract'].notna().all():raise ValueError('usable contract undefined')
        if not bars.loc[bars.usable,'source_count'].eq(interval).all():raise ValueError('usable bucket incomplete')
        if bars.loc[bars.source_count.eq(0),['open','high','low','close','volume']].notna().any().any():raise ValueError('empty synthetic price/volume')
        if bars.loc[~bars.calendar_valid,'usable'].any():raise ValueError('uncertified calendar used')
        if interval==5:
            mapped_valid=bars.feature_valid.to_numpy(bool)
        else:
            pos=np.searchsorted(five.available_at.array.asi8,bars.timestamp.array.asi8,side='right')-1
            mapped_valid=np.zeros(len(bars),bool);eligible=pos>=0;source=five.iloc[pos[eligible]]
            mapped_valid[eligible]=source.feature_valid.to_numpy(bool)&source.usable.to_numpy(bool)&(source.contract.to_numpy()==bars.loc[eligible,'contract'].to_numpy())
        ready=bars.usable.to_numpy(bool)&mapped_valid
        years=bars.timestamp.dt.tz_convert('America/New_York').dt.year.to_numpy()
        for year in (2018,2019,2020):
            mask=years==year
            recorded=coverage[(coverage['product']==product)&(coverage.interval_minutes==interval)&(coverage.year==year)].iloc[0]
            row=dict(product=product,interval_minutes=interval,year=year,scheduled_slots=int(mask.sum()),
                usable_slots=int(bars.usable.to_numpy(bool)[mask].sum()),mapped_ready_slots=int(ready[mask].sum()),
                ready_sessions=int(bars.loc[mask&ready,'session'].nunique()))
            for key in ('scheduled_slots','usable_slots','mapped_ready_slots','ready_sessions'):
                if int(recorded[key])!=row[key]:raise ValueError('decision coverage mismatch')
            computed.append(row)
        rosters.append(dict(product=product,interval_minutes=interval,scheduled_slots=len(bars),
            earliest_timestamp=bars.timestamp.min().isoformat(),latest_completion=bars.available_at.max().isoformat(),
            empty_slots=int(bars.source_count.eq(0).sum()),calendar_invalid_slots=int((~bars.calendar_valid).sum()),
            ready_development_slots=int(ready[(years>=2018)&(years<=2020)].sum())))
qualification=json.loads((stage/'data-preparation/provenance-qualification.json').read_text())
for record in [qualification['missing_raw_mapping']]+qualification['unavailable_raw_condition_records']:
    if (pub/record['path']).is_file():raise ValueError('raw prerequisite availability changed; fresh audit needed')
checks={}
for name in ('reconciliation.json','seed-sensitivity.json','independent-bar-aggregation-verification.json',
             'independent-feature-verification.json','source-correction.json','calendar-exclusions.csv',
             'source-quality.csv','numerical-tests-corrected.json','preparation-observation.json'):
    p=stage/'data-preparation'/name;checks[name]=dict(path=p.relative_to(stage).as_posix(),sha256=sha256_file(p),bytes=p.stat().st_size)
reconciliation=json.loads((stage/'data-preparation/reconciliation.json').read_text())
if not all(r['passed'] and not any(r['mismatch_counts'].values()) for r in reconciliation.values()):raise ValueError('retained reconciliation nonpassing')
exclusions=pd.read_csv(stage/'data-preparation/calendar-exclusions.csv')
if exclusions.duplicated(['product','session']).any():raise ValueError('ambiguous calendar exclusions')
seeds=json.loads((stage/'data-preparation/seed-sensitivity.json').read_text())
receipt=dict(schema_version='study21.data-review/v1',status='passed_with_recorded_qualifications',
    stage_id=stage.name,created_at=datetime.now(timezone.utc).isoformat(),
    checker=dict(path=Path(__file__).relative_to(stage).as_posix(),sha256=sha256_file(Path(__file__))),
    command=[sys.executable,str(Path(__file__).resolve())],signals_computed=False,outcomes_computed=False,
    input_lock=dict(path='inputs.lock.json',sha256=sha256_file(lock_path)),
    pinned_delivery=lock['delivery'],current_source_inventory_sha256=sha256_file(inventory_path),
    verified_published_and_support_files=verified,historical_producer_resolution=historical,
    frozen_bhishma_sources_verified=frozen_count,
    decision_coverage_sha256=sha256_file(coverage_path),decision_coverage_reconciled=computed,rosters=rosters,
    essential_consumed_input_support='Verified pinned unadjusted published 1m partitions, stable instrument/roll identities, adjusted reconciliation artifacts and immutable six-cell causal delivery provide sufficient support for the authorized historical descriptive Stage 1 study.',
    reconstruction_limitations=['Original raw volume-rank-0 mapping and raw condition JSON records are unavailable. Original-source reconstruction is not established.',
        'ES roll-1 point-in-time definition-pair prerequisite belongs to 2010 reconstruction; this study consumes 2017 warmup/2018–2020 price inputs. No source rebuild or missing mapping was invented.',
        'Condition summaries survive in the pinned original manifests; absent original condition JSON bytes are not verified.',
        'Original mapping arrival/publication times and actual feed receipt timing are unavailable. This is not certified live-feed reconstruction.'],
    coverage_qualifications=dict(calendar_policy=lock['calendar_policy'],calendar_excluded_session_counts={str(k):int(v) for k,v in exclusions.groupby('product').size().items()},
        warmup='250 consecutive usable same-contract 5m observations fixed; unknown gaps and uncertified sessions reset state. 500 is input-only readiness/first-open seed sensitivity.',
        primary_and_500_seed_support=seeds,quality='No-trade absence remains unknown missing input; primary completeness is conservative, reducing overnight and GC support. Holiday clocks are rule-generated, not individually certified.'),
    retained_check_identities=checks,essential_blockers=blockers,
    assurance_limit='Input integrity and coverage/provenance review; no validation of event outcomes, statistics, report claims, profitability or external backup. Independent numerical/outcome/report reviewers provide separate receipts.')
with receipt_path.open('x') as f:json.dump(receipt,f,indent=2,allow_nan=False);f.write('\n')
print(json.dumps(dict(status=receipt['status'],receipt_path=str(receipt_path),receipt_sha256=sha256_file(receipt_path),verified_market_support_files=len(verified),historical_producer_files=len(historical),frozen_bhishma_sources=frozen_count,essential_blockers=blockers),indent=2))
