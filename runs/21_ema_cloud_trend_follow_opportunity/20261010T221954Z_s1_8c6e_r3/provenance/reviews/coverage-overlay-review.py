"""Independent saved-ledger coverage review; imports no research producers."""
from datetime import datetime,timezone
from pathlib import Path
import hashlib
import json
import sys
import numpy as np
import pandas as pd
import pyarrow.parquet as pq

folder=Path(__file__).resolve().parent;stage=folder.parents[1]
pre_path=folder/'coverage-overlay-preexecution.json'
pre=json.loads(pre_path.read_text());result_path=folder/'coverage-overlay-review.json'
if result_path.exists():raise FileExistsError('fresh scientific receipt required')
def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for data in iter(lambda:f.read(8<<20),b''):h.update(data)
    return h.hexdigest()
def verify_pins():
    for record in pre['pins']:
        path=Path(record['path'])
        if digest(path)!=record['sha256'] or path.stat().st_size!=record['bytes']:raise ValueError('pinned input drift '+str(path))
    if digest(Path(__file__))!=pre['checker_sha256']:raise ValueError('checker source drift')
verify_pins()
config=json.loads((stage/'config.json').read_text())
if config['session_strata']!={'Asia':[18,24,0,3],'Europe':[3,9],'US':[9,16],'Late':[16,18]}:
    raise ValueError('checker requires the declared frozen clock bins')
manifest=json.loads((stage/'events.manifest.json').read_text());cache={};ledger_scope=[]
label_checks=0;accepted_by_cell={}
for record in manifest['records']:
    if record['role']!='technical':continue
    columns=['timestamp','product','interval_minutes','usable','feature_valid','ema20','ema50','side','accepted','session']
    tech=pq.ParquetFile(record['path']).read(columns=columns).to_pandas()
    local=pd.to_datetime(tech.timestamp,utc=True).dt.tz_convert('America/New_York')
    dev=local.dt.year.between(2018,2020)
    tech=tech.loc[dev].reset_index(drop=True);local=local.loc[dev].reset_index(drop=True)
    year=local.dt.year;month=local.dt.strftime('%Y-%m')
    calendar=local.dt.tz_localize(None).dt.normalize()
    week=(calendar-pd.to_timedelta(calendar.dt.dayofweek,unit='D')).dt.strftime('%Y-%m-%d')
    hour=local.dt.hour
    bins=np.where((hour>=18)|(hour<3),'Asia',np.where(hour<9,'Europe',np.where(hour<16,'US','Late')))
    trade_date=(calendar+pd.to_timedelta((hour>=18).astype(int),unit='D')).dt.strftime('%Y-%m-%d')
    eligible=tech.usable.fillna(False).astype(bool)&tech.feature_valid.fillna(False).astype(bool)
    finite=np.isfinite(tech.ema20.to_numpy(float))&np.isfinite(tech.ema50.to_numpy(float))
    buy=eligible.to_numpy()&finite&(tech.ema20.to_numpy(float)>tech.ema50.to_numpy(float))
    sell=eligible.to_numpy()&finite&(tech.ema20.to_numpy(float)<tech.ema50.to_numpy(float))
    derived_side=np.where(buy,'Buy',np.where(sell,'Sell','None'))
    if not np.array_equal(derived_side,tech.side.to_numpy()):raise ValueError('technical side labels differ from independent EMA direction')
    if not np.array_equal(trade_date.to_numpy(),tech.session.astype(str).to_numpy()):raise ValueError('saved trading session differs from independent 18:00 NY date rule')
    labels={'year':year.astype(str).to_numpy(),'month':month.to_numpy(),'week':week.to_numpy(),
            'hour':hour.astype(str).to_numpy(),'time_stratum':bins,'session':trade_date.to_numpy()}
    accepted=tech.accepted.fillna(False).astype(bool).to_numpy()
    product=record['product'];interval=int(record['interval_minutes'])
    accepted_by_cell[f'{product}/{interval}m']=int(accepted.sum())
    for side,mask in [('All',np.ones(len(tech),bool)),('Buy',buy),('Sell',sell)]:
        for kind,label in labels.items():
            grouped=pd.DataFrame({'period':label[mask],'eligible':eligible.to_numpy()[mask],
                                  'accepted':accepted[mask]}).groupby('period',sort=False).agg(
                                      scheduled=('period','size'),eligible=('eligible','sum'),accepted=('accepted','sum'))
            for period,scheduled,evaluable,events in grouped.itertuples():
                cache[(product,interval,side,kind,str(period))]=(int(scheduled),int(evaluable),int(events))
    label_checks+=len(tech)*2
    ledger_scope.append(dict(product=product,interval_minutes=interval,
                             development_slots_checked=len(tech),accepted_events=int(accepted.sum()),
                             path=record['path'],sha256=record['sha256']))
fields=['scheduled_slots','eligible_slots','unknown_signal_slots','coverage_complete','zero_event_qualification']
mismatches=[];scopes=[]
for name in ['S1-T04_stability.csv','S1-T05_calendar.csv']:
    table=pd.read_csv(stage/'tables'/name,dtype={'period':str,'direction':str})
    if table.row_id.duplicated().any():raise ValueError('duplicate table row identity')
    if set(table.support)!={'all'} or set(table.horizon)!={15}:raise ValueError('unexpected overlay table support/horizon')
    for row in table.itertuples(index=False):
        key=(row.product,int(row.interval_minutes),row.direction,row.period_kind,str(row.period))
        scheduled,eligible_count,accepted_count=cache.get(key,(0,0,0))
        unknown=scheduled-eligible_count
        complete=scheduled>0 and unknown==0
        qualification='events_observed' if accepted_count>0 else 'auditable_eligible_support' if eligible_count>0 else 'no_eligible_support'
        expected=dict(scheduled_slots=scheduled,eligible_slots=eligible_count,unknown_signal_slots=unknown,
                      coverage_complete=complete,zero_event_qualification=qualification)
        for field,value in expected.items():
            actual=getattr(row,field)
            if actual!=value:mismatches.append(dict(table=name,row_id=row.row_id,column=field,expected=value,actual=str(actual)))
        if int(row.accepted)!=accepted_count:
            mismatches.append(dict(table=name,row_id=row.row_id,column='accepted_cross_check',expected=accepted_count,actual=str(row.accepted)))
    scopes.append(dict(table=name,rows_checked=len(table),coverage_fields_checked=fields,
        coverage_cells_checked=len(table)*len(fields),accepted_cells_cross_checked=len(table),
        period_kinds=sorted(table.period_kind.unique()),directions=sorted(table.direction.unique()),
        units=sorted(table.unit.unique()),zero_event_rows=int(table.accepted.eq(0).sum())))
verify_pins()
receipt=dict(schema_version='study21.coverage-overlay-review/v1',status='passed' if not mismatches else 'failed',
    stage_id=stage.name,created_at=datetime.now(timezone.utc).isoformat(),
    checker_sha256=digest(Path(__file__)),preexecution_pin_file_sha256=digest(pre_path),
    command=pre['command'],producer_modules_imported=False,outcomes_scored=False,estimators_written=False,
    table_scope=scopes,total_rows_checked=sum(r['rows_checked'] for r in scopes),
    total_coverage_cells_checked=sum(r['coverage_cells_checked'] for r in scopes),
    accepted_cells_cross_checked=sum(r['accepted_cells_cross_checked'] for r in scopes),
    independent_calendar_and_side_labels_checked=label_checks,technical_ledgers=ledger_scope,
    accepted_by_cell=accepted_by_cell,grouped_support_keys=len(cache),mismatch_count=len(mismatches),mismatches=mismatches[:50],
    definitions=dict(eligible='usable AND feature_valid',week='NY calendar Monday of signal open',month='NY year-month of signal open',
        session='NY date plus one calendar day for open hour >=18',direction='usable valid finite cloud: Buy EMA20>EMA50, Sell EMA20<EMA50, equality/undefined None',
        coverage_complete='positive scheduled directional-cohort slots and no ineligible slots in that cohort',
        zero_event_qualification='accepted>0 events_observed; accepted=0 and eligible>0 auditable_eligible_support; accepted=0 and eligible=0 no_eligible_support'),
    qualification='Buy/Sell support is conditional on a defined valid cloud direction; undefined-direction slots remain in All coverage only. A Buy/Sell coverage_complete flag therefore does not certify complete market-feed or whole-calendar coverage. Unknown slots and feature readiness remain visible in All rows.',
    assurance_scope='Every S1-T04/T05 saved row coverage overlay and accepted-count cross-check only; no outcome paths, estimates, uncertainty or report values recalculated.')
with result_path.open('x') as f:json.dump(receipt,f,indent=2,allow_nan=False);f.write('\n')
print(json.dumps({k:receipt[k] for k in ['status','total_rows_checked','total_coverage_cells_checked','accepted_cells_cross_checked','mismatch_count','grouped_support_keys']},indent=2))
print('receipt_sha256='+digest(result_path))
if mismatches:sys.exit(1)
