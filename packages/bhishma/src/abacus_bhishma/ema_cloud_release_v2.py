"""New immutable 1.1.0 input-only extension; the 1.0.0 release is preserved.

Minute prices are consumed one UTC-year partition at a time. Independent 3m/5m
aggregation precedes chronological concatenation; five-minute recurrences run
on the combined roster, so processing boundaries never reset feature state.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import gc
import importlib.metadata
import json
from pathlib import Path
import shutil
import subprocess
import sys

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

from .continuous_loader import open_continuous_dataset, price_to_float
from .ema_cloud import NY, expected_minutes, aggregate_minutes, add_features, load_pinned_5m, load_release as load_v1
from .ema_cloud_loader_v2 import DATASET_ID, VERSION
from .ema_cloud_release import write_json, descriptor, verify_record, reconciliation, seed_audit
from .paths import load_workspace_paths
from .provenance import sha256_file

OLD_MANIFEST_SHA256 = '59010a558b4e727dbfaa37a64b4a209590288f23744127ab98747cd27ff56d44'
ENDPOINT = pd.Timestamp('2026-09-18T21:00:00Z')
PREFIX_ENDPOINT = pd.Timestamp('2021-01-01T05:00:00Z')


def scientific_prefix_parity(old, extended, endpoint=PREFIX_ENDPOINT):
    """Exact inherited fields, dtypes and nulls, including unusable slots."""
    prefix = extended.loc[extended.available_at.le(endpoint)].reset_index(drop=True)
    if list(old.columns) != list(prefix.columns):
        raise ValueError('input prefix scientific column inventory mismatch')
    if len(old) != len(prefix):
        raise ValueError('input prefix scheduled-row inventory mismatch')
    mismatches = [name for name in old if not old[name].reset_index(drop=True).equals(prefix[name])]
    if mismatches:
        raise ValueError('input prefix scientific values/dtypes differ: ' + ','.join(mismatches))
    return dict(status='passed', rows=len(old), fields=len(old.columns), cells=len(old)*len(old.columns),
                tolerance=0, columns=list(old.columns), dtypes={c:str(old[c].dtype) for c in old},
                excluded_wrapper_columns=[], prefix_endpoint=endpoint.isoformat())


def integer_aggregation_check(source, bars, interval):
    """Independent fixed-point group extrema/order/sums for every usable bar."""
    raw = source.copy()
    raw['_bucket'] = raw.ts_event.dt.floor(f'{interval}min')
    grouped = raw.groupby('_bucket', sort=True).agg(open=('open','first'), high=('high','max'),
        low=('low','min'), close=('close','last'), volume=('volume','sum'),
        source_count=('ts_event','size'), contract_count=('instrument_id','nunique'),
        contains_roll=('is_roll','any'))
    usable = bars.loc[bars.usable].set_index('timestamp')
    independent = grouped.reindex(usable.index)
    mismatches = {name:int(np.count_nonzero(usable[name].to_numpy() != price_to_float(independent[name])))
                  for name in ('open','high','low','close')}
    for name in ('volume','source_count','contract_count','contains_roll'):
        mismatches[name] = int(np.count_nonzero(usable[name].to_numpy() != independent[name].to_numpy()))
    result = dict(status='passed' if not any(mismatches.values()) else 'failed', interval_minutes=interval,
                  usable_rows=len(usable), fields=8, cells=len(usable)*8, tolerance=0, mismatch_counts=mismatches)
    if result['status'] != 'passed':
        raise ValueError(f'independent integer aggregation differs: {result}')
    return result


def combine_roster(chunks, interval):
    """Recover global closure flags and run features once across processing cuts."""
    bars=pd.concat(chunks,ignore_index=True).sort_values('timestamp',kind='stable').reset_index(drop=True)
    if bars.timestamp.duplicated().any():
        raise ValueError('processing boundary duplicated a scheduled slot')
    bars['known_closure_before']=(bars.timestamp.diff()>pd.Timedelta(minutes=interval)).fillna(False)
    if interval==5:
        return add_features(bars,warmup=250)
    bars['feature_valid']=False
    return bars


def _source_identity(source, master, rolls, product):
    fields=['product','roll_id','instrument_id','raw_symbol','maturity_year','maturity_month',
            'mapping_start','mapping_end','instrument_class','min_price_increment']
    joined = source.merge(master[fields], on=['product','roll_id'], how='left', suffixes=('','_master'), validate='many_to_one')
    bad = ((joined.instrument_id != joined.instrument_id_master) | (joined.raw_symbol != joined.raw_symbol_master)
           | joined.maturity_year.isna() | (joined.instrument_class != 'F')
           | (joined.mapping_start != joined.mapping_start_master) | (joined.mapping_end != joined.mapping_end_master))
    if bad.any() or source.ts_event.duplicated().any():
        raise ValueError('source minute identity/duplicate mismatch')
    sessions = pd.to_datetime(source.session_date)
    if ((sessions < pd.to_datetime(source.mapping_start)) | (sessions >= pd.to_datetime(source.mapping_end))).any():
        raise ValueError('source minute mapping bounds mismatch')
    roll = rolls.loc[rolls['product'].eq(product)].set_index('roll_id')
    support = joined.roll_id.gt(0)
    if not np.array_equal(joined.loc[support,'instrument_id'], roll.loc[joined.loc[support,'roll_id'],'new_instrument_id']):
        raise ValueError('source minute versus authoritative roll schedule mismatch')
    prices = source[['open','high','low','close']].to_numpy(dtype=np.int64)
    tick = joined.min_price_increment.to_numpy(dtype=np.int64)
    price_invalid = ((prices<=0).any(axis=1) | (prices[:,1]<prices[:,0]) | (prices[:,1]<prices[:,3])
                     | (prices[:,2]>prices[:,0]) | (prices[:,2]>prices[:,3]) | (prices[:,1]<prices[:,2]))
    if price_invalid.any() or (tick<=0).any() or source.volume.lt(0).any():
        raise ValueError('invalid primary OHLCV or master tick')
    tick_invalid = ((prices % tick[:,None]) != 0).any(axis=1)
    transformed = source.rename(columns={'ts_event':'timestamp'}).copy()
    for name in ('open','high','low','close'):
        transformed[name] = price_to_float(source[name])
    transformed['source_valid'] = ~tick_invalid
    transformed['contract'] = [f'{product}:{iid}:{int(y)}:{int(m)}:{sym}' for iid,y,m,sym in
        zip(joined.instrument_id,joined.maturity_year,joined.maturity_month,joined.raw_symbol)]
    return transformed, int(tick_invalid.sum())


def prepare_release(workspace: Path | str, audit_dir: Path | str, release_id: str):
    paths = load_workspace_paths(workspace)
    root, audit = paths.publication_root, Path(audit_dir)
    final = root/'data/features/ema_cloud'/f'version={VERSION}'
    manifest_path = root/'catalog/datasets'/f'{DATASET_ID}.json'
    quality_path = root/'reports/quality'/f'{DATASET_ID}.md'
    staging = root/'data/staging/ema_cloud'/release_id
    schema_path = root/'catalog/schemas'/f'{DATASET_ID}.json'
    indicator_path = root/'catalog/indicators'/f'{DATASET_ID}.json'
    if any(p.exists() for p in (final,manifest_path,quality_path,staging,indicator_path)):
        raise FileExistsError('fresh EMA1.1 release identity required; no overwrite or recovery')
    audit.mkdir(parents=True, exist_ok=True)
    staging.mkdir(parents=True)
    manifests, manifest_pins, consumed = {}, [], []
    for name in ('volume_lead_unadjusted_v1','volume_lead_back_adjusted_v1','tv_indicators__dridr_ohlcv_5m__v1'):
        path=root/'catalog/datasets'/f'{name}.json'
        manifests[name]=json.loads(path.read_text())
        manifest_pins.append(descriptor(root,path,role='input_manifest'))
        for record in manifests[name]['output_files']:
            consumed.append(verify_record(root,record)|dict(role='published_input_byte_verification',dataset=name))
    base = manifests['volume_lead_unadjusted_v1']
    if not base['validation']['passed']:
        raise ValueError('published primary validation failed')
    old_path = root/'catalog/datasets/same_contract_ema_cloud__1.0.0.json'
    if sha256_file(old_path) != OLD_MANIFEST_SHA256:
        raise ValueError('immutable original delivery identity mismatch')
    old_manifest = json.loads(old_path.read_text())
    old_pin=descriptor(root,old_path,role='exact_scientific_prefix_authority')
    consumed.append(old_pin)
    for record in old_manifest['output_files'] + old_manifest.get('auxiliary_files',[]):
        consumed.append(verify_record(root,record)|dict(role='old_release_prefix_or_producer_support'))
    unavailable=[]
    for record in base['source_files']:
        if record['path'].endswith('condition.json'):
            if (root/record['path']).is_file():
                consumed.append(verify_record(root,record)|dict(role='condition_report'))
            else:
                unavailable.append(record|dict(status='unavailable_not_verified'))
    for relative in ('catalog/calendars/cme_fixed_clock_session_v1.json',
                     f'requests/inbox/{DATASET_ID}.yaml', f'catalog/schemas/{DATASET_ID}.json'):
        consumed.append(descriptor(root,root/relative,role='input_contract'))
    source_root=Path(__file__).parent
    for name in ('ema_cloud_release_v2.py','ema_cloud_loader_v2.py','ema_cloud.py','ema_cloud_release.py',
                 'calendar.py','continuous_loader.py','manifest_selection.py','paths.py','provenance.py'):
        original=source_root/name; dest=staging/'provenance'/name
        dest.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(original,dest)
        consumed.append(descriptor(root,original,role='executed_data_source'))
    shutil.copyfile(paths.workspace_root/'uv.lock',staging/'provenance/uv.lock')
    consumed.append(descriptor(root,paths.workspace_root/'uv.lock',role='environment_lock'))
    environment=dict(python=sys.version, packages={name:importlib.metadata.version(name) for name in ('numpy','pandas','pyarrow')},
                     executable=sys.executable, argv=sys.argv, locked_environment_no_sync=True)
    write_json(audit/'environment.json',environment)
    status=subprocess.run(['git','status','--porcelain=v1','--untracked-files=all'],cwd=paths.workspace_root,capture_output=True,text=True,check=True)
    (audit/'git-status.txt').write_text(status.stdout)
    master=pq.ParquetFile(root/'data/curated/instruments/roll=volume_lead_v1/instrument_master.parquet').read().to_pandas()
    rolls=pq.ParquetFile(root/'data/curated/continuous/1m/roll=volume_lead_v1/roll_schedule.parquet').read().to_pandas()
    if master[['product','roll_id']].duplicated().any():
        raise ValueError('ambiguous published instrument master')
    counts, qualities, excluded, integer_checks, retained_checks, prefix_checks, outputs = [],[],[],[],[],[],[]
    seeds, terminal_checks = {}, []
    for product in ('ES','GC','NQ'):
        chunks={3:[],5:[]}
        base_path=root/'catalog/datasets/volume_lead_unadjusted_v1.json'
        dataset=open_continuous_dataset(root,product,manifest_path=base_path,
            expected_manifest_sha256=sha256_file(base_path),verify_selected_files=True)
        for year in range(2017,2027):
            print(f'input-only {product}/{year}',flush=True)
            source=dataset.to_table(filter=pc.field('year')==year).to_pandas().sort_values('ts_event').reset_index(drop=True)
            source=source.loc[source.ts_event.lt(ENDPOINT)].reset_index(drop=True)
            transformed,tick_bad=_source_identity(source,master,rolls,product)
            end=f'{year+1}-01-01' if year<2026 else '2026-09-19'
            schedule=expected_minutes(product,f'{year}-01-01',end)
            schedule=schedule.loc[schedule.timestamp.lt(ENDPOINT)].reset_index(drop=True)
            outside=transformed.loc[~transformed.timestamp.isin(schedule.timestamp)]
            qualities.append(dict(product=product,year=year,source_rows=len(source),tick_deviations=tick_bad,
                price_invalid_rows=0,identity_mismatches=0,duplicates=0,roll_schedule_mismatches=0,
                source_rows_outside_normal_schedule=len(outside),first_source_timestamp=source.ts_event.min().isoformat(),
                last_source_timestamp=source.ts_event.max().isoformat()))
            outside[['timestamp','session_date','product','raw_symbol','instrument_id','roll_id']].to_csv(audit/f'{product}-{year}-outside-normal-schedule.csv',index=False)
            ex=schedule.loc[~schedule.calendar_valid,['session','calendar_event']].drop_duplicates().copy()
            ex['product']=product; excluded.append(ex)
            retained=load_pinned_5m(root,root/'catalog/datasets/tv_indicators__dridr_ohlcv_5m__v1.json',
                sha256_file(root/'catalog/datasets/tv_indicators__dridr_ohlcv_5m__v1.json'),product,(year,))
            for interval in (3,5):
                bars=aggregate_minutes(transformed,interval,schedule,product)
                bars=bars.loc[bars.available_at.le(ENDPOINT)].reset_index(drop=True)
                # The guard remains active; its internal helper flag is represented
                # by quality_reason, preserving the inherited scientific schema.
                bars=bars.drop(columns=['missing_contract_source'])
                integer_checks.append(integer_aggregation_check(source,bars,interval)|dict(product=product,year=year))
                if interval==5:
                    retained_checks.append(reconciliation(source,bars,retained)|dict(product=product,year=year))
                chunks[interval].append(bars)
            if year==2026:
                terminal=transformed.loc[transformed.session_date.astype(str).eq('2026-09-18')]
                expected=schedule.loc[schedule.session.eq('2026-09-18')]
                missing=len(set(expected.timestamp)-set(terminal.timestamp))
                extra=len(set(terminal.timestamp)-set(expected.timestamp))
                if len(terminal)!=1380 or missing or extra or not terminal.source_valid.all() or terminal.contract.nunique()!=1:
                    raise ValueError('final source session not complete and usable')
                terminal_checks.append(dict(product=product,expected_minutes=1380,observed_minutes=len(terminal),
                    missing_minutes=missing,outside_minutes=extra,source_tick_invalid=0,contract_count=1,
                    source_last_timestamp=terminal.timestamp.max().isoformat(),modeled_completion=ENDPOINT.isoformat(),status='passed'))
            del source, transformed, schedule, retained, bars
            gc.collect()
        for interval in (3,5):
            bars=combine_roster(chunks[interval],interval)
            chunks[interval].clear()
            if interval==5:
                seeds[product]=seed_audit(bars)
                seeds[product]['all_history_ready_250']=int(bars.feature_valid.sum())
                seeds[product]['all_history_ready_500']=int((bars.usable & bars.consecutive_count.ge(500)).sum())
            old=load_v1(root,product=product,interval=interval,manifest_path=old_path,expected_manifest_sha256=OLD_MANIFEST_SHA256)
            prefix_checks.append(scientific_prefix_parity(old,bars)|dict(product=product,interval_minutes=interval))
            for year, group in bars.groupby(bars.timestamp.dt.tz_convert(NY).dt.year,sort=True):
                counts.append(dict(product=product,interval_minutes=interval,year=int(year),scheduled_slots=len(group),
                    usable_slots=int(group.usable.sum()),feature_ready_slots=int(group.feature_valid.sum()) if interval==5 else None,
                    missing_slots=int(group.quality_reason.str.contains('missing_source_minutes').sum()),empty_slots=int(group.source_count.eq(0).sum()),
                    mixed_slots=int(group.contract_count.gt(1).sum()),calendar_invalid_slots=int((~group.calendar_valid).sum()),
                    expected_source_minutes=int(group.expected_count.sum()),observed_source_minutes=int(group.source_count.sum()),
                    known_closures_before=int(group.known_closure_before.sum())))
            destination=staging/f'product={product}'/f'interval={interval}m/part-000.parquet'
            destination.parent.mkdir(parents=True,exist_ok=True)
            pq.write_table(pa.Table.from_pandas(bars,preserve_index=False),destination,compression='zstd')
            outputs.append(dict(path=(final/destination.relative_to(staging)).relative_to(root).as_posix(),bytes=destination.stat().st_size,
                sha256=sha256_file(destination),product=product,interval_minutes=interval,role='bars3' if interval==3 else 'bars5features',rows=len(bars)))
            del bars,old
            gc.collect()
    pd.DataFrame(counts).to_csv(audit/'coverage.csv',index=False)
    pd.DataFrame(qualities).to_csv(audit/'source-quality.csv',index=False)
    pd.concat(excluded).sort_values(['product','session']).to_csv(audit/'calendar-exclusions.csv',index=False)
    write_json(audit/'integer-aggregation-reconciliation.json',dict(status='passed',checks=integer_checks))
    write_json(audit/'retained-5m-reconciliation.json',dict(status='passed',checks=retained_checks))
    write_json(audit/'seed-sensitivity.json',seeds)
    write_json(audit/'endpoint-coverage.json',dict(status='passed',endpoint=ENDPOINT.isoformat(),checks=terminal_checks))
    prefix=dict(status='passed',old_manifest=old_pin,new_dataset_id=DATASET_ID,
        prefix_endpoint=PREFIX_ENDPOINT.isoformat(),tolerance=0,excluded_wrapper_columns=[],
        old_output_files=old_manifest['output_files'],new_output_files=outputs,
        cells=sum(r['cells'] for r in prefix_checks),records=prefix_checks,
        checker=descriptor(root,Path(__file__),role='prefix_checker'))
    write_json(audit/'input-prefix-parity.json',prefix)
    qualified=dict(status='published_input_provenance_sufficient_with_qualifications',
        unavailable_raw_condition_records=unavailable,
        source_reconstruction='Missing original raw mapping and ES historical roll-1 definition pair prevent original source reconstruction; no mappings invented and no published input rebuilt.',
        published_consumption='All declared primary/reconciliation output bytes verified; consumed 2017–2026 selected minute identities reconcile to master and roll schedule. Independent 3m/5m integer aggregation and exact retained5m adjustment translation passed.',
        calendar='Normal weekday18–17NY; ES/NQ16:15–16:30 pause only before session-date2021-06-28. Rule-generated uncertified holidays/short sessions retained unusable and reset. Missing/no-trade source minutes never inferred as closures.',
        timing='available_at is modeled exclusive candle close; actual vendor/mapping receipt times unavailable.',
        scientific_prefix='All inherited 1.0.0 scientific columns, dtypes and nulls reproduce exactly through original completion endpoint; no columns excluded.',
        feature_continuity='Combined full roster before EMA/ATR; calendar/source/contract resets only, no year/fold/split reset.',
        unverified='Annual holiday certification, native TradingView equivalence and off-device backup.',
        outcome_scope='Input-only2017 causal warmup through2026-09-18 completion; no signals/candidate-conditioned outcomes or rankings.')
    write_json(audit/'provenance-qualification.json',qualified)
    lock=dict(schema_version=1,dataset_id=DATASET_ID,scope='causal input-only2017–2026',input_manifests=manifest_pins,
              files=consumed,calendar_policy=qualified['calendar'],feature_warmup=250,endpoint=ENDPOINT.isoformat(),price_basis='unadjusted same-contract')
    write_json(audit/'inputs.lock.json',lock)
    # Refuse drift before the new publication is made visible.
    for record in manifest_pins+consumed:
        verify_record(root,record)
    for path in audit.iterdir():
        if path.is_file():
            dest=staging/'audit'/path.name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,dest)
    manifest=dict(dataset_id=DATASET_ID,version=VERSION,release_id=release_id,created_at=datetime.now(timezone.utc).isoformat(),
        output_files=outputs,source_manifest_pins=manifest_pins,source_files=consumed,calendar_policy=qualified['calendar'],
        features=old_manifest['features'],coverage_start_session='2017-01-02',coverage_end_completion=ENDPOINT.isoformat(),
        qualifications=qualified,validation=dict(passed=True,scientific_prefix=prefix,independent_integer_checks=len(integer_checks),retained_5m_checks=len(retained_checks)),
        schema_path=schema_path.relative_to(root).as_posix(),quality_report_path=quality_path.relative_to(root).as_posix(),
        auxiliary_files=[dict(path=(final/p.relative_to(staging)).relative_to(root).as_posix(),bytes=p.stat().st_size,sha256=sha256_file(p))
                         for p in sorted(staging.rglob('*')) if p.is_file() and 'product=' not in str(p)])
    final.parent.mkdir(parents=True,exist_ok=True);staging.rename(final)
    write_json(manifest_path,manifest)
    write_json(indicator_path,dict(name='Same-contract5m EMA20/50 and WilderATR14 continuous2017–2026',version=VERSION,
        feature_manifest=dict(path=manifest_path.relative_to(root).as_posix(),sha256=sha256_file(manifest_path)),parameters=manifest['features'],
        schema=schema_path.relative_to(root).as_posix(),audit=(final/'audit').relative_to(root).as_posix()))
    quality_path.parent.mkdir(parents=True,exist_ok=True)
    with quality_path.open('x') as stream:
        stream.write('# Same-contract EMA cloud1.1.0 input delivery\n\nContinuous causal2017 warmup through September18,2026 17:00NY. No candidate outcomes.\n\n')
        stream.write(qualified['calendar']+'\n\n'+qualified['source_reconstruction']+' '+qualified['published_consumption']+'\n\n')
        stream.write(f"Exact prefix: {prefix['cells']:,} inherited scientific cells, zero tolerance/mismatches, no excluded fields. 250-observation warmup preserved;500 support/seed sensitivity saved.\n\n")
        stream.write('Every product finalsession has1380 observed/expected minutes, one contract, no missing/tick-invalid minutes; actual completion21:00UTC. Full quality/calendar/coverage details and source snapshots are retained in the immutable audit directory.\n\n')
        stream.write(qualified['timing']+' '+qualified['unverified']+' remain unverified. Prior Abacus market-history exposure remains a study qualification.\n')
    record_paths=[root/r['path'] for r in manifest_pins+consumed+outputs+manifest['auxiliary_files']]
    record_paths += [manifest_path,schema_path,indicator_path,quality_path]
    unique=sorted(set(record_paths))
    consumed_records=[dict(path=str(p.resolve()),bytes=p.stat().st_size,sha256=sha256_file(p)) for p in unique]
    return dict(delivery=dict(path=str(manifest_path.resolve()),bytes=manifest_path.stat().st_size,sha256=sha256_file(manifest_path),version=VERSION),
                consumed_records=consumed_records,output_files=outputs,input_prefix_parity=str(final/'audit/input-prefix-parity.json'),
                audit_dir=str(audit),endpoint=ENDPOINT.isoformat(),status='passed')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace',required=True);parser.add_argument('--audit-dir',required=True);parser.add_argument('--release-id',required=True)
    args=parser.parse_args()
    result=prepare_release(args.workspace,args.audit_dir,args.release_id)
    write_json(Path(args.audit_dir)/'release-result.json',result)
    print(json.dumps(result,indent=2,allow_nan=False))


if __name__=='__main__':main()
