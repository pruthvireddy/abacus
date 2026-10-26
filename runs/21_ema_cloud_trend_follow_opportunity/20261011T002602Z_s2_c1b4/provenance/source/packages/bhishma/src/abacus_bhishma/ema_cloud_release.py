"""Immutable publication and input-only audit for same-contract EMA bars."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
import json
import shutil

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

from .continuous_loader import open_continuous_dataset, price_to_float
from .ema_cloud import DATASET_ID, VERSION, NY, expected_minutes, aggregate_minutes, add_features, load_pinned_5m
from .paths import load_workspace_paths
from .provenance import sha256_file


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as f:
        json.dump(value, f, indent=2, allow_nan=False)
        f.write('\n')


def descriptor(root, path, **extra):
    return dict(path=path.relative_to(root).as_posix(), bytes=path.stat().st_size,
                sha256=sha256_file(path), **extra)


def verify_record(root, record):
    path=root/record['path']
    actual=descriptor(root,path)
    if actual['sha256']!=record['sha256'] or actual['bytes']!=record['bytes']:
        raise ValueError(f"published input byte mismatch: {path}")
    return actual


def reconciliation(source_fixed, rebuilt, retained):
    """Independent integer-price aggregation vs exact adjusted translation."""
    selected=source_fixed.copy()
    selected['timestamp']=selected.ts_event.dt.floor('5min')
    raw=selected.groupby('timestamp',sort=True).agg(
        open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last'),
        volume=('volume','sum'),source_count=('ts_event','size'), instrument_id=('instrument_id','first'),
        roll_id=('roll_id','first'),contains_roll=('is_roll','any'))
    usable=rebuilt.loc[rebuilt.usable,'timestamp']
    retained=retained.rename(columns={'ts_event':'timestamp'}).set_index('timestamp')
    join=raw.loc[raw.index.isin(usable)].join(retained,rsuffix='_retained',how='inner')
    comparable=join[(~join.is_mixed_contract_bar)&(~join.is_mixed_adjustment_bar)&join.price_adjustment.notna()]
    mismatch={}
    for column in ['open','high','low','close']:
        mismatch[column]=int((comparable[column].to_numpy(dtype=np.int64) !=
                            comparable[column+'_retained'].to_numpy(dtype=np.int64)-comparable.price_adjustment.to_numpy(dtype=np.int64)).sum())
    for column in ['volume','instrument_id','roll_id','contains_roll']:
        mismatch[column]=int((comparable[column]!=comparable[column+'_retained']).sum())
    mismatch['source_count']=int((comparable.source_count!=comparable.source_bar_count).sum())
    # Also reconcile reusable float OHLC to the independent raw integer result.
    independent=rebuilt.loc[rebuilt.usable].set_index('timestamp').join(raw,rsuffix='_fixed')
    errors={column:float(np.max(np.abs(independent[column].to_numpy()-price_to_float(independent[column+'_fixed'])),initial=0.))
            for column in ['open','high','low','close']}
    mismatch['rebuilt_price_float']=sum(v>1e-9 for v in errors.values())
    mismatch['rebuilt_volume']=int((independent.volume!=independent.volume_fixed).sum())
    result=dict(usable_rebuilt=len(independent),retained_compatible=len(comparable),
                unmatched_usable=int(len(independent)-len(comparable)),
                mismatch_counts=mismatch,float_error_max_points=errors,
                adjustment_translation='retained fixed-point OHLC minus exact price_adjustment',
                passed=not any(mismatch.values()) and len(independent)==len(comparable))
    if not result['passed']:
        raise ValueError(f"five-minute reconciliation failed: {result}")
    return result


def seed_audit(features):
    """Input-only 250/500 support and alternative first-open seed error bound."""
    counts=features.consecutive_count.to_numpy()
    valid=features.usable.to_numpy()
    first=features.feature_reset.to_numpy() & valid
    seed_delta=pd.Series(np.where(first,np.abs(features.open-features.close),np.nan)).ffill().fillna(0).to_numpy()
    error20=seed_delta*np.power(19/21,np.maximum(counts-1,0))
    error50=seed_delta*np.power(49/51,np.maximum(counts-1,0))
    result={}
    dev=features.timestamp.dt.tz_convert(NY).dt.year.between(2018,2020).to_numpy()
    for warmup in (250,500):
        mask=valid&(counts>=warmup)&dev
        result[str(warmup)]=dict(ready_5m_slots=int(mask.sum()),
            max_alternate_first_open_seed_error_ema20_points=float(np.max(error20[mask],initial=0.)),
            max_alternate_first_open_seed_error_ema50_points=float(np.max(error50[mask],initial=0.)))
    result['definition']='Same causal recurrences, seed sensitivity to first-open rather than first-close; no outcome or signal comparison; 500 changes readiness only.'
    return result


def prepare_release(workspace: Path | str, audit_dir: Path | str, release_id: str):
    """Prepare, audit and publish fresh reusable inputs; never score outcomes."""
    paths=load_workspace_paths(workspace)
    root=paths.publication_root
    audit_dir=Path(audit_dir)
    audit_dir.mkdir(parents=True,exist_ok=True)
    final=root/'data/features/ema_cloud'/f'version={VERSION}'
    manifest_path=root/'catalog/datasets'/f'{DATASET_ID}.json'
    quality_path=root/'reports/quality'/f'{DATASET_ID}.md'
    staging=root/'data/staging/ema_cloud'/release_id
    if any(x.exists() for x in [final,manifest_path,quality_path,staging]):
        raise FileExistsError('fresh EMA release/staging identity required')
    staging.mkdir(parents=True)
    manifests={}
    pins=[]
    for name in ['volume_lead_unadjusted_v1','volume_lead_back_adjusted_v1','tv_indicators__dridr_ohlcv_5m__v1']:
        path=root/'catalog/datasets'/f'{name}.json'
        manifests[name]=json.loads(path.read_text())
        pins.append(descriptor(root,path,role='input_manifest'))
    base=manifests['volume_lead_unadjusted_v1']
    if not base['validation']['passed']:
        raise ValueError('published base validation not passed')
    input_records=[]
    # Pin actual scientific input partitions and auxiliary bytes. The public
    # primary loader separately verifies every declared selected product file.
    for name,m in manifests.items():
        for record in m['output_files']:
            path=record['path']
            if 'year=' not in path or any(f'year={y}/' in path for y in (2017,2018,2019,2020)):
                input_records.append(verify_record(root,record)|dict(role='published_input',dataset=name))
    unavailable_originals=[]
    for record in base['source_files']:
        if record['path'].endswith('condition.json'):
            if (root/record['path']).is_file():
                input_records.append(verify_record(root,record)|dict(role='condition_report'))
            else:
                unavailable_originals.append(record|dict(status='unavailable_not_verified'))
    calendar=root/'catalog/calendars/cme_fixed_clock_session_v1.json'
    input_records.append(descriptor(root,calendar,role='normal_regime_reference'))
    source_root=Path(__file__).parent
    for name in ['ema_cloud.py','ema_cloud_release.py','calendar.py','continuous_loader.py','manifest_selection.py','paths.py','provenance.py']:
        path=source_root/name
        dest=staging/'provenance'/name
        dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(path,dest)
        input_records.append(descriptor(root,path,role='executed_data_source'))
    shutil.copyfile(paths.workspace_root/'uv.lock',staging/'provenance/uv.lock')
    input_records.append(descriptor(root,paths.workspace_root/'uv.lock',role='environment_lock'))
    master_path=root/'data/curated/instruments/roll=volume_lead_v1/instrument_master.parquet'
    roll_path=root/'data/curated/continuous/1m/roll=volume_lead_v1/roll_schedule.parquet'
    master=pq.ParquetFile(master_path).read().to_pandas()
    rolls=pq.ParquetFile(roll_path).read().to_pandas()
    if master[['product','roll_id']].duplicated().any():
        raise ValueError('ambiguous published instrument master')
    fields=['product','roll_id','instrument_id','raw_symbol','maturity_year','maturity_month','mapping_start','mapping_end','instrument_class','min_price_increment']
    counts=[];row_audits=[];calendars=[];reconciliations={};seeds={};outputs=[]
    endpoint=pd.Timestamp('2021-01-01',tz=NY).tz_convert('UTC')
    for product in ('ES','GC','NQ'):
        print(f'preparing {product}',flush=True)
        base_path=root/'catalog/datasets/volume_lead_unadjusted_v1.json'
        dataset=open_continuous_dataset(root,product,manifest_path=base_path,
                  expected_manifest_sha256=sha256_file(base_path),verify_selected_files=True)
        table=dataset.to_table(filter=(pc.field('year')>=2017)&(pc.field('year')<=2020))
        source=table.to_pandas().sort_values('ts_event').reset_index(drop=True)
        if source.ts_event.duplicated().any():
            raise ValueError('duplicate primary minute')
        joined=source.merge(master[fields],on=['product','roll_id'],how='left',suffixes=('','_master'),validate='many_to_one')
        bad=(joined.instrument_id!=joined.instrument_id_master)|(joined.raw_symbol!=joined.raw_symbol_master)|joined.maturity_year.isna()|(joined.instrument_class!='F')
        bad|=(joined.mapping_start!=joined.mapping_start_master)|(joined.mapping_end!=joined.mapping_end_master)
        if bad.any():raise ValueError(f'published instrument identity mismatch: {product} {int(bad.sum())}')
        sess=pd.to_datetime(source.session_date)
        bad=(sess< pd.to_datetime(source.mapping_start)) | (sess>=pd.to_datetime(source.mapping_end))
        if bad.any():raise ValueError('source mapping bounds mismatch')
        # Compare selected contracts to authoritative roll schedule per interval.
        r=rolls[rolls['product']==product].set_index('roll_id')
        support=joined.roll_id>0
        rid=joined.loc[support,'roll_id']
        if not np.array_equal(joined.loc[support,'instrument_id'].to_numpy(),r.loc[rid,'new_instrument_id'].to_numpy()):
            raise ValueError('source contract versus roll schedule mismatch')
        ohlc=source[['open','high','low','close']].to_numpy(dtype=np.int64)
        tick=joined.min_price_increment.to_numpy(dtype=np.int64)
        tick_bad=int(((ohlc % tick[:,None])!=0).any(axis=1).sum())
        # Some historical GC contract ticks differ from today's tick; the master
        # is used per mapping interval and the observed deviations are disclosed.
        price_bad=int(((ohlc<=0).any(axis=1)|(ohlc[:,1]<ohlc[:,0])|(ohlc[:,1]<ohlc[:,3])|
                      (ohlc[:,2]>ohlc[:,0])|(ohlc[:,2]>ohlc[:,3])).sum())
        if price_bad:raise ValueError('invalid primary price rows')
        source_float=source.rename(columns={'ts_event':'timestamp'}).copy()
        for name in ['open','high','low','close']:
            source_float[name]=price_to_float(source[name])
        source_float['source_valid']=~((ohlc % tick[:,None])!=0).any(axis=1)
        source_float['contract']=[f'{product}:{iid}:{int(y)}:{int(m)}:{sym}' for iid,y,m,sym in
                                  zip(joined.instrument_id,joined.maturity_year,joined.maturity_month,joined.raw_symbol)]
        schedule=expected_minutes(product,'2017-01-01','2021-01-02')
        schedule=schedule[schedule.timestamp<endpoint].reset_index(drop=True)
        excluded=schedule.loc[~schedule.calendar_valid,['session','calendar_event']].drop_duplicates()
        excluded['product']=product;calendars.append(excluded)
        observed_outside=source_float.loc[~source_float.timestamp.isin(schedule.timestamp)]
        outside_record=dict(product=product,source_rows=len(source),duplicate_rows=0,identity_mismatches=0,
                            roll_schedule_mismatches=0,price_invalid_rows=price_bad,tick_deviations=tick_bad,
                            source_rows_outside_normal_schedule=len(observed_outside),
                            first_source_timestamp=source.ts_event.min().isoformat(),
                            last_source_timestamp=source.ts_event.max().isoformat())
        row_audits.append(outside_record)
        observed_outside[['timestamp','session_date','product','raw_symbol','instrument_id','roll_id']].to_csv(audit_dir/f'{product}-outside-normal-schedule.csv',index=False)
        retained_path=root/'catalog/datasets/tv_indicators__dridr_ohlcv_5m__v1.json'
        retained=load_pinned_5m(root,retained_path,sha256_file(retained_path),product,(2017,2018,2019,2020))
        for interval in (3,5):
            bars=aggregate_minutes(source_float,interval,schedule,product)
            bars=bars[bars.available_at<=endpoint].reset_index(drop=True)
            if interval==5:
                bars=add_features(bars)
                reconciliations[product]=reconciliation(source,bars,retained)
                seeds[product]=seed_audit(bars)
            else:
                bars['feature_valid']=False
            for year in (2017,2018,2019,2020):
                group=bars[bars.timestamp.dt.tz_convert(NY).dt.year==year]
                counts.append(dict(product=product,interval_minutes=interval,year=year,
                    split='warmup_only' if year==2017 else 'development',scheduled_slots=len(group),
                    usable_slots=int(group.usable.sum()),feature_ready_slots=int(group.feature_valid.sum()) if interval==5 else None,
                    missing_slots=int(group.quality_reason.str.contains('missing_source_minutes').sum()),
                    empty_slots=int((group.source_count==0).sum()),mixed_slots=int((group.contract_count>1).sum()),
                    calendar_invalid_slots=int((~group.calendar_valid).sum()),
                    expected_source_minutes=int(group.expected_count.sum()),observed_source_minutes=int(group.source_count.sum()),
                    known_closures_before=int(group.known_closure_before.sum())))
            destination=staging/f'product={product}'/f'interval={interval}m/part-000.parquet'
            destination.parent.mkdir(parents=True,exist_ok=True)
            pq.write_table(pa.Table.from_pandas(bars,preserve_index=False),destination,compression='zstd')
            relative=destination.relative_to(staging)
            outputs.append(dict(path=(final/relative).relative_to(root).as_posix(),sha256=sha256_file(destination),
                                bytes=destination.stat().st_size,product=product,interval_minutes=interval,
                                role='bars3' if interval==3 else 'bars5features',rows=len(bars)))
    pd.DataFrame(counts).to_csv(audit_dir/'coverage.csv',index=False)
    pd.DataFrame(row_audits).to_csv(audit_dir/'source-quality.csv',index=False)
    pd.concat(calendars).sort_values(['product','session']).to_csv(audit_dir/'calendar-exclusions.csv',index=False)
    write_json(audit_dir/'reconciliation.json',reconciliations)
    write_json(audit_dir/'seed-sensitivity.json',seeds)
    missing_mapping=next(r for r in base['source_files'] if 'symbology/continuous' in r['path'])
    qualified=dict(status='published_input_provenance_sufficient_with_qualifications',
        missing_raw_mapping=dict(**missing_mapping,present=(root/missing_mapping['path']).is_file()),
        unavailable_raw_condition_records=unavailable_originals,
        condition_record_scope='Pinned original release manifests retain source-condition summaries; absent original raw condition JSON bytes are not verified.',
        source_reconstruction='Missing raw mapping and ES roll-1 definition pair prevent source reconstruction checks. No mappings invented; existing releases not rebuilt.',
        published_consumption='Verified actual retained minute partitions, master, roll schedule, adjusted reconciliation partitions and adjustment schedules; selected 2017–2020 contract identity reconciles to master and rolls.',
        essential_for_this_delivery='Published byte and lineage identities are sufficient for this historical descriptive study. Original mapping arrival/publication times remain unavailable; this is not certified live-feed reconstruction.',
        historical_roll1='ES roll_id 1 pertains to 2010-06-14 and is not consumed for 2017–2020 features. Its existing published adjustment translation is checked rather than recomputed.',
        calendar='Normal weekday 18–17 NY, ES/NQ 16:15–16:30 pre-2021 pause; rule-generated holiday/early-close sessions unusable, all nominal slots retained. Missing no-trade minutes are unknown gaps, never inferred closures.',
        outcome_scope='No signals or outcomes calculated by preparation; only 2017 causal warmup and 2018–2020 input bars.')
    write_json(audit_dir/'provenance-qualification.json',qualified)
    lock=dict(schema_version=1,dataset_id=DATASET_ID,scope='input-only 2017 warmup, 2018–2020 price roster',
              publication_root='configured ABACUS_PUBLICATION_ROOT or paths.local.toml',input_manifests=pins,
              files=input_records,calendar_policy=qualified['calendar'],feature_warmup=250,
              price_basis='unadjusted same contract',endpoint=endpoint.isoformat())
    write_json(audit_dir/'inputs.lock.json',lock)
    manifest=dict(dataset_id=DATASET_ID,version=VERSION,release_id=release_id,
        created_at=datetime.now(timezone.utc).isoformat(),output_files=outputs,
        source_manifest_pins=pins,source_files=input_records,
        calendar_policy=qualified['calendar'],features=dict(ema_lengths=[20,50],ema_seed='first_close',
            atr_length=14,atr_seed='mean_first_14_true_ranges; segment-first TR=high-low',
            warmup=250,resets='contract switches, invalid slots, unknown gaps',availability='modeled exclusive candle close'),
        coverage_start_session='2017-01-02',coverage_end_completion=endpoint.isoformat(),
        qualifications=qualified,validation=dict(passed=True,reconciliation=reconciliations),
        quality_report_path=quality_path.relative_to(root).as_posix())
    # Audit records and source bytes remain with the immutable delivery.
    for path in audit_dir.iterdir():
        if path.is_file():
            dest=staging/'audit'/path.name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,dest)
    manifest['auxiliary_files']=[dict(path=(final/p.relative_to(staging)).relative_to(root).as_posix(),
                                     bytes=p.stat().st_size,sha256=sha256_file(p))
                                 for p in sorted(staging.rglob('*')) if p.is_file() and 'product=' not in str(p)]
    final.parent.mkdir(parents=True,exist_ok=True)
    staging.rename(final)
    write_json(manifest_path,manifest)
    quality_path.parent.mkdir(parents=True,exist_ok=True)
    with quality_path.open('x') as f:
        f.write('# Same-contract EMA cloud input delivery 1.0.0\n\n')
        f.write('Input-only preparation for 2017 warmup and 2018–2020 history. No event labels or future outcomes.\n\n')
        f.write(qualified['calendar']+'\n\n')
        f.write(qualified['source_reconstruction']+' '+qualified['published_consumption']+'\n\n')
        f.write('Primary 250 consecutive complete 5m observations after reset remains fixed. A 500-observation readiness and first-open seed sensitivity is saved in the immutable audit directory.\n\n')
        f.write('Manifest: `catalog/datasets/'+DATASET_ID+'.json`. Exact per-product/year coverage, exclusions, source quality, reconciliations and qualifications are saved below `data/features/ema_cloud/version=1.0.0/audit/`.\n')
    return dict(manifest_path=str(manifest_path),manifest_sha256=sha256_file(manifest_path),
                output_files=outputs,audit_dir=str(audit_dir))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace',required=True);parser.add_argument('--audit-dir',required=True);parser.add_argument('--release-id',required=True)
    args=parser.parse_args()
    print(json.dumps(prepare_release(args.workspace,args.audit_dir,args.release_id),indent=2))


if __name__=='__main__':main()
