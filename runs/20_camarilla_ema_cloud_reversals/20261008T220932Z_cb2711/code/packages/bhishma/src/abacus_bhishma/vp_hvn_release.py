"""Versioned NQ evening snapshots, built through the public continuous loader."""
from __future__ import annotations

import argparse
from collections import deque
from dataclasses import asdict
from datetime import date, datetime, time, timedelta, timezone
import hashlib
import json
from pathlib import Path
import shutil
import time as clock
from zoneinfo import ZoneInfo

import numpy as np
import pyarrow as pa
import pyarrow.dataset as ds
import pyarrow.parquet as pq

from .continuous_loader import open_continuous_dataset, price_to_float
from .paths import resolve_publication_root
from .vp_hvn import Profile, composite, enable_native, match_nodes, select
from .session_anchored_vwap import holiday_sessions

DATASET_ID = "nq_causal_vp_hvn__1.0.0"
NY = ZoneInfo("America/New_York")
MINUTE = 60_000_000_000
SOURCE_SHA = "6fb8254d661c41e8a867953e608886bf367ee3a759a110eab41f2469d373e8ee"


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def dump(path, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False)+'\n')


def session_start(day):
    return datetime.combine(day-timedelta(days=1), time(18), NY)


def week_key(day):
    """Globex trading week: Monday trading date begins Sunday 18:00 NY."""
    return day-timedelta(days=day.weekday())


def expected_session_minutes(day):
    # Known historical equity pause, not a reason to exclude evening windows.
    out = np.arange(1380)
    if day < date(2021, 6, 28):
        out = out[(out < 1335) | (out >= 1350)]
    return out


def verify_inputs(root, workspace):
    contract = json.loads((root/f'catalog/indicators/{DATASET_ID}.spec.json').read_text())
    records = []
    for r in contract['input_manifests']:
        p = root/r['manifest_path']
        if sha256(p) != r['sha256']:
            raise ValueError(f"manifest identity mismatch: {p}")
        records.append({'path': r['manifest_path'], 'sha256': r['sha256']})
    pine = root/contract['indicator_source']['path']
    if sha256(pine) != SOURCE_SHA:
        raise ValueError('supplied indicator changed')
    for name in ('volume_lead_unadjusted_v1', 'volume_lead_back_adjusted_v1'):
        m = json.loads((root/f'catalog/datasets/{name}.json').read_text())
        for r in m['output_files']:
            if '/product=NQ/' in r['path'] or any(s in r['path'] for s in ('schedule','factors','instrument_master')):
                if sha256(root/r['path']) != r['sha256']:
                    raise ValueError(f"partition identity mismatch: {r['path']}")
                record={'path':r['path'], 'sha256':r['sha256']}
                if '/product=NQ/' in r['path']:
                    stamp=pq.ParquetFile(root/r['path']).read(columns=['ts_event'])['ts_event'].combine_chunks().to_numpy().astype('datetime64[ns]').astype(np.int64)
                    if np.any(np.diff(stamp)<=0):raise ValueError('source partition not uniquely ordered')
                    record['strict_original_order_verified']=True
                records.append(record)
    return records


def load_bars(root, start=None, end=None):
    filt = None
    if start:
        filt = ds.field('session_date') >= date.fromisoformat(start)
    if end:
        other = ds.field('session_date') < date.fromisoformat(end)
        filt = other if filt is None else filt & other
    names = ['ts_event','session_date','open','high','low','close','volume','raw_symbol',
             'instrument_id','roll_id','is_roll','source_batch','mapping_start','mapping_end']
    raw = open_continuous_dataset(root, 'NQ').to_table(columns=names, filter=filt).sort_by('ts_event')
    adjusted = open_continuous_dataset(root, 'NQ', 'back_adjusted').to_table(
        columns=names+['price_adjustment'], filter=filt).sort_by('ts_event')
    if len(raw) != len(adjusted):
        raise ValueError('adjusted/raw length mismatch')
    data = {n: raw[n].combine_chunks().to_numpy(zero_copy_only=False) for n in names}
    data['ts_event'] = data['ts_event'].astype('datetime64[ns]').astype(np.int64)
    if np.any(np.diff(data['ts_event']) <= 0):
        raise ValueError('timestamps must be unique and ordered')
    for n in names:
        if n not in ('open','high','low','close') and not raw[n].equals(adjusted[n]):
            raise ValueError(f'adjusted lineage mismatch: {n}')
    offset = adjusted['price_adjustment'].combine_chunks().to_numpy()
    for n in ('open','high','low','close'):
        ap = adjusted[n].combine_chunks().to_numpy()
        if not np.array_equal(ap, data[n]+offset):
            raise ValueError(f'adjustment price mismatch: {n}')
        if np.any(data[n] % 250_000_000):
            raise ValueError(f'off-tick fixed-point prices: {n}')
        data[n+'_fixed'] = data[n].copy()
        # Encoding is exactly quarter-point aligned. Recover that exact binary
        # grid after the public float conversion, avoiding floor(3.99999...).
        data[n] = np.rint(price_to_float(data[n])*4)/4
    if np.any(data['low'] > np.minimum(data['open'],data['close'])) or np.any(data['high'] < np.maximum(data['open'],data['close'])) or np.any(data['low'] > data['high']):
        raise ValueError('invalid OHLC')
    day_values=data['session_date'].astype('datetime64[D]')
    starts=data['mapping_start'].astype('datetime64[D]');ends=data['mapping_end'].astype('datetime64[D]')
    if np.any(day_values<starts) or np.any(day_values>=ends):
        raise ValueError('bar outside its mapping interval')
    schedule=pq.ParquetFile(root/'data/curated/continuous/1m/roll=volume_lead_v1/roll_schedule.parquet').read().to_pylist()
    for record in schedule:
        if record['product']!='NQ':continue
        mask=data['roll_id']==record['roll_id']
        if mask.any() and (not np.all(data['instrument_id'][mask]==record['new_instrument_id']) or not np.all(data['raw_symbol'][mask]==record['new_raw_symbol'])):
            raise ValueError('bar disagrees with roll schedule')
    if np.any(offset % 250_000_000):
        raise ValueError('adjustment off the NQ quarter-point grid')
    data['adjustment'] = np.rint(price_to_float(offset)*4)/4
    return data


NODE = pa.struct([('candidate_id',pa.string()),('node_id',pa.string()),('lo',pa.float64()),
                  ('hi',pa.float64()),('mid',pa.float64()),('strength',pa.float64()),
                  ('side',pa.int8()),('rank',pa.int8()),('available_at',pa.int64()),
                  ('match_ambiguous',pa.bool_())])
DECISION = pa.struct([('candidate_id',pa.string()),('node_id',pa.string()),('reason',pa.string())])
SNAPSHOT = pa.schema(
    [(n,pa.int64()) for n in ('ts_event','available_at','rebuild_at','adj_rebuild_at')]+
    [(n,pa.string()) for n in ('session_date','week','raw_symbol','source_batch','season')]+
    [(n,pa.int32()) for n in ('minute','instrument_id','roll_id')]+
    [(n,pa.bool_()) for n in ('is_roll','overnight_complete','overnight_contract_clean','hvn_complete','hvn_contract_clean','reference_complete','reference_contract_clean','source_degraded','hvn_source_degraded','reference_source_degraded')]+
    [(n,pa.float64()) for n in ('open','high','low','close','volume','adjustment','previous_close','volatility60','pdh','pdl')]+
    [(n,pa.float64()) for n in [f'{prefix}{kind}_{level}' for prefix in ('','adj_') for kind in ('on','post_on','cw','pw','rth') for level in ('vah','poc','val')]]+
    [('references',pa.list_(pa.float64())),('adj_references',pa.list_(pa.float64()))]+
    [(n,pa.list_(NODE)) for n in ('selected','post_selected','adj_selected')])
DECISIONS = pa.schema([('ts_event',pa.int64()),('session_date',pa.string()),
                       ('decisions',pa.list_(DECISION)),('adj_decisions',pa.list_(DECISION))])


def build(root, workspace, stage, start=None, end=None):
    """Feature-only replay. No trade signals or forward price outcomes."""
    compiler = enable_native(workspace/'work/bhishma/native')
    integrity = verify_inputs(root, workspace)
    data = load_bars(root, start, end)
    stage.mkdir(parents=True, exist_ok=False)
    dump(stage/'integrity.json', integrity)
    dump(stage/'compiler.json', compiler)
    manifest = json.loads((root/'catalog/datasets/volume_lead_unadjusted_v1.json').read_text())
    degraded = set(manifest['condition_reports']['ohlcv_1m']['degraded_dates'])
    holidays = holiday_sessions('NQ',2010,2026)
    profiles = [Profile(),Profile()]
    prev_week = [(np.nan,)*3,(np.nan,)*3]
    prev_week_symbols, week_symbols = set(), set()
    week_complete = False; prev_week_complete = False
    week_degraded = False; prev_week_degraded = False; prior_rth_degraded = False
    current_week = None; week_sessions = 0
    prior_rth = [(np.nan,)*3,(np.nan,)*3]
    prior_rth_symbols = set(); prior_rth_complete = False
    previous_session = None; previous_observed_in_on = False
    history = deque(maxlen=10)
    previous_close = np.nan
    tr_history = deque(maxlen=60); tr_times = deque(maxlen=60)
    ts = data['ts_event']
    days = data['session_date'].astype('datetime64[D]')
    bounds = np.r_[0,np.flatnonzero(days[1:] != days[:-1])+1,len(days)]
    rows, candidates, decisions, sessions, rhythm = [], [], [], [], []
    year = None; files = []; total_rows = 0; last_on = [Profile(),Profile()]

    def write(name, entries, y, schema=None):
        if not entries:
            return
        p = stage/name/f'year={y}'/'part-000.parquet'
        p.parent.mkdir(parents=True, exist_ok=True)
        table = pa.Table.from_pylist(entries, schema=schema)
        pq.write_table(table,p,compression='zstd')
        files.append({'path':str(p.relative_to(stage)),'sha256':sha256(p),'rows':len(entries),'bytes':p.stat().st_size,'table':name,'year':y})

    def flush(y):
        write('snapshots',rows,y,SNAPSHOT);write('decisions',decisions,y,DECISIONS)
        write('candidates',candidates,y);write('sessions',sessions,y);write('rhythm',rhythm,y)
        rows.clear();candidates.clear();decisions.clear();sessions.clear();rhythm.clear()

    started = clock.monotonic()
    for number,(a,b) in enumerate(zip(bounds[:-1],bounds[1:])):
        day = date.fromisoformat(str(days[a]))
        if year is not None and day.year != year:
            flush(year)
            print(f'feature year {year}: {total_rows:,} snapshots, {clock.monotonic()-started:.1f}s',flush=True)
        year = day.year
        sdate = day.isoformat(); start_time = int(session_start(day).timestamp()*1e9)
        minutes = (ts[a:b]-start_time)//MINUTE
        if np.any(ts[a:b]%MINUTE) or np.any(minutes<0) or np.any(minutes>=1440):
            raise ValueError(f'bar outside source trading-date interval: {sdate}')
        h,l,v,c,adj = (data[x][a:b] for x in ('high','low','volume','close','adjustment'))
        symbols = set(data['raw_symbol'][a:b])
        fut_mask=minutes<1380
        complete = np.array_equal(minutes[fut_mask], expected_session_minutes(day))
        utc_days = {datetime.fromtimestamp(int(x)/1e9,timezone.utc).date().isoformat() for x in (ts[a],ts[b-1])}
        day_degraded = bool(utc_days & degraded)
        wk = week_key(day)
        if wk != current_week:
            if current_week is not None:
                prev_week = [p.calculate() for p in profiles]
                prev_week_symbols = week_symbols.copy()
                prev_week_complete = week_complete and week_sessions == 5
                prev_week_degraded = week_degraded
            for p in profiles: p.reset()
            current_week,wk_first = wk,day.weekday()==0
            week_symbols=set();week_complete=wk_first;week_sessions=0;week_degraded=False
        # All enabled references remain literal, even where consumers exclude
        # incomplete or mixed-contract histories. Never shorten HVN lookback.
        on = last_on
        # Source ON reset is an in/out transition. If the previous session ends
        # while still in ON, retain its state and flag the discontinuity.
        previous_in_on = previous_observed_in_on
        if not previous_in_on:
            for p in on: p.reset()
        on_clean_start = not previous_in_on and len(minutes) and minutes[0]==0
        on_complete = on_clean_start
        pdh = previous_session['high'] if previous_session else np.nan
        pdl = previous_session['low'] if previous_session else np.nan
        ref_symbols = week_symbols | prev_week_symbols | prior_rth_symbols | (previous_session['symbols'] if previous_session else set())
        reference_complete = week_complete and prev_week_complete and prior_rth_complete and bool(previous_session and previous_session['complete'])
        history_complete = len(history)==10 and all(x['complete'] for x in history)
        history_symbols = set().union(*(x['symbols'] for x in history)) if history else set()
        history_high = np.concatenate([x['high'] for x in history]) if history else np.empty(0)
        history_low = np.concatenate([x['low'] for x in history]) if history else np.empty(0)
        history_volume = np.concatenate([x['volume'] for x in history]) if history else np.empty(0)
        history_adj = np.concatenate([x['adjustment'] for x in history]) if history else np.empty(0)
        if len(history_high)+int(fut_mask.sum())>90000:
            raise ValueError('one-minute history unexpectedly exceeds source capacity')
        nodes,adj_nodes = [],[]; rebuilt = adj_rebuilt = None
        current_symbols=set();overnight_degraded=False
        for j,minute in enumerate(minutes):
            i = a+j; t = int(ts[i]); adjustment = float(adj[j])
            evening = minute < 360
            overnight_degraded |= bool(datetime.fromtimestamp(t/1e9,timezone.utc).date().isoformat() in degraded)
            if evening:
                if minute != j: on_complete=False
                cw = [p.calculate() for p in profiles]
                on_values = [p.calculate() for p in on]
                raw_refs = [pdh,pdl,*cw[0],*prev_week[0],*prior_rth[0],*on_values[0]]
                adjusted_pdh = previous_session['adj_high'] if previous_session else np.nan
                adjusted_pdl = previous_session['adj_low'] if previous_session else np.nan
                adjusted_refs = [adjusted_pdh,adjusted_pdl,*cw[1],*prev_week[1],*prior_rth[1],*on_values[1]]
                chosen,reasons = select(nodes,previous_close,raw_refs)
                adj_chosen,adj_reasons = select(adj_nodes,previous_close+adjustment,adjusted_refs)
                def saved(ns,chosen,available,shift=0.0):
                    return [dict(candidate_id=ns[k].candidate_id,node_id=ns[k].node_id,
                                 lo=ns[k].lo-shift,hi=ns[k].hi-shift,mid=ns[k].mid-shift,
                                 strength=ns[k].strength,side=side,rank=rank,
                                 available_at=available,match_ambiguous=ns[k].match_ambiguous) for k,side,rank in chosen]
                cutoff = int(ts[i-1]+MINUTE) if i else t-MINUTE
                all_symbols = current_symbols | {data['raw_symbol'][i]}
                tr_ready = len(tr_times)==60 and tr_times[0]==t-60*MINUTE and tr_times[-1]==t-MINUTE
                r = dict(ts_event=t,available_at=cutoff,rebuild_at=rebuilt,adj_rebuild_at=adj_rebuilt,
                         session_date=sdate,week=wk.isoformat(),minute=int(minute),
                         raw_symbol=data['raw_symbol'][i],instrument_id=int(data['instrument_id'][i]),
                         roll_id=int(data['roll_id'][i]),is_roll=bool(data['is_roll'][i]),source_batch=data['source_batch'][i],
                         season='EDT' if session_start(day).dst() else 'EST',
                         overnight_complete=bool(on_complete and minute>0),
                         overnight_contract_clean=bool(len(all_symbols)==1 and on_clean_start),
                         hvn_complete=bool(history_complete),hvn_contract_clean=bool(len(history_symbols|all_symbols)==1),
                         reference_complete=bool(reference_complete),reference_contract_clean=bool(len(ref_symbols|all_symbols)==1),
                         source_degraded=bool(overnight_degraded),
                         hvn_source_degraded=bool(any(x['degraded'] for x in history) or overnight_degraded),
                         reference_source_degraded=bool(week_degraded or prev_week_degraded or prior_rth_degraded or (previous_session and previous_session['degraded']) or overnight_degraded),
                         open=float(data['open'][i]),high=float(h[j]),low=float(l[j]),close=float(c[j]),volume=float(v[j]),
                         adjustment=adjustment,previous_close=float(previous_close),
                         volatility60=float(np.mean(tr_history)) if tr_ready else np.nan,
                         pdh=float(pdh),pdl=float(pdl),references=raw_refs,
                         adj_references=[x-adjustment for x in adjusted_refs],
                         selected=saved(nodes,chosen,rebuilt),adj_selected=saved(adj_nodes,adj_chosen,adj_rebuilt,adjustment))
                for mode,prefix in ((0,''),(1,'adj_')):
                    for label,levels in (('on',on_values[mode]),('cw',cw[mode]),('pw',prev_week[mode]),('rth',prior_rth[mode])):
                        r.update({f'{prefix}{label}_{k}':float(value)-(adjustment if mode else 0.0) for k,value in zip(('vah','poc','val'),levels)})
                decisions.append(dict(ts_event=t,session_date=sdate,
                                      decisions=[dict(candidate_id=n.candidate_id,node_id=n.node_id,reason=reasons[k]) for k,n in enumerate(nodes)],
                                      adj_decisions=[dict(candidate_id=n.candidate_id,node_id=n.node_id,reason=adj_reasons[k]) for k,n in enumerate(adj_nodes)]))
            # Incorporate this completed bar after saving its pre-bar state.
            for mode,p in enumerate(profiles):p.add(h[j]+(adjustment if mode else 0),l[j]+(adjustment if mode else 0),v[j])
            if minute<930:
                for mode,p in enumerate(on):p.add(h[j]+(adjustment if mode else 0),l[j]+(adjustment if mode else 0),v[j])
            current_symbols.add(data['raw_symbol'][i])
            tr = max(h[j]-l[j],abs(h[j]-previous_close),abs(l[j]-previous_close)) if np.isfinite(previous_close) else h[j]-l[j]
            tr_history.append(tr);tr_times.append(t);previous_close=c[j]
            if evening:
                # New session makes prior afternoon candidate caches irrelevant
                # from its first completed bar. Other sessions' bars are retained.
                if rebuilt is None or t+MINUTE-rebuilt>=15*MINUTE:
                    hh=np.r_[history_high,h[:j+1]];ll=np.r_[history_low,l[:j+1]];vv=np.r_[history_volume,v[:j+1]]
                    aa=np.r_[history_adj,adj[:j+1]]
                    for mode in (0,1):
                        before = nodes if mode==0 else adj_nodes
                        nn,meta = composite(hh+(aa if mode else 0),ll+(aa if mode else 0),vv)
                        rebuild_id = f'{sdate}:{minute:03d}:{mode}'
                        nn = match_nodes(nn,before,rebuild_id)
                        if not np.isclose(meta['mass'],meta['input_volume'],rtol=1e-10,atol=1e-6):
                            raise ValueError('composite volume not conserved')
                        for n in nn:
                            candidates.append(dict(**asdict(n),session_date=sdate,rebuild_id=rebuild_id,
                                                   available_at=t+MINUTE,coordinate='adjusted' if mode else 'contract',
                                                   profile_rows=int(meta['rows']),profile_step=float(meta['step']),
                                                   profile_low=float(meta['base']),mass=float(meta['mass']),input_volume=float(meta['input_volume']),
                                                   bar_count=len(vv),completed_sessions=len(history)))
                        if mode==0:nodes=nn;rebuilt=t+MINUTE
                        else:adj_nodes=nn;adj_rebuilt=t+MINUTE
                for mode,prefix in ((0,''),(1,'adj_')):
                    r.update({f'{prefix}post_on_{k}':float(value)-(adjustment if mode else 0) for k,value in zip(('vah','poc','val'),on[mode].calculate())})
                post_refs=[pdh,pdl,*profiles[0].calculate(),*prev_week[0],*prior_rth[0],*on[0].levels]
                post_chosen,_=select(nodes,c[j],post_refs)
                r['post_selected']=saved(nodes,post_chosen,rebuilt)
                rows.append(r);total_rows+=1
        # Complete all intraday reference state before the next evening.
        for p in on:p.calculate()
        rth = (minutes>=930)&(minutes<1320)
        if rth.any():
            for mode in (0,1):
                rp=Profile();rp.add_batch(h[rth]+(adj[rth] if mode else 0),l[rth]+(adj[rth] if mode else 0),v[rth])
                prior_rth[mode]=rp.calculate()
            prior_rth_symbols=set(data['raw_symbol'][a:b][rth])
            prior_rth_complete=np.array_equal(minutes[rth],np.arange(930,1320))
            prior_rth_degraded=day_degraded
        week_symbols |= symbols;week_complete &= bool(complete);week_sessions+=1;week_degraded |= day_degraded
        if fut_mask.any():
            previous_session=dict(high=float(h[fut_mask].max()),low=float(l[fut_mask].min()),adj_high=float((h+adj)[fut_mask].max()),adj_low=float((l+adj)[fut_mask].min()),
                                  symbols=symbols,complete=bool(complete),degraded=day_degraded,last_minute=int(minutes[-1]))
            history.append(dict(high=h[fut_mask].copy(),low=l[fut_mask].copy(),volume=v[fut_mask].copy(),adjustment=adj[fut_mask].copy(),symbols=symbols,complete=bool(complete),degraded=day_degraded))
        previous_observed_in_on=bool(minutes[-1]<930)
        sessions.append(dict(session_date=sdate,week=wk.isoformat(),year=day.year,
                             source_rows=b-a,expected_rows=len(expected_session_minutes(day)),complete=bool(complete),
                             futures_rows=int(fut_mask.sum()),outside_futures_rows=int((~fut_mask).sum()),
                             evening_rows=int((minutes<360).sum()),missing_evening_minutes=360-int((minutes<360).sum()),
                             symbols='|'.join(sorted(symbols)),is_roll=bool(data['is_roll'][a:b].any()),
                             hvn_history_complete=bool(history_complete),reference_complete=bool(reference_complete),
                             hvn_contract_clean=bool(len(history_symbols|symbols)==1),reference_contract_clean=bool(len(ref_symbols|symbols)==1),
                             season='EDT' if session_start(day).dst() else 'EST'))
        sessions[-1]['holiday_names']='|'.join(holidays.get(day,[]))
        for bin_start in range(0,360,15):
            mask=(minutes>=bin_start)&(minutes<bin_start+15)
            if mask.any():
                indices=np.flatnonzero(mask)
                rhythm.append(dict(session_date=sdate,year=day.year,season=sessions[-1]['season'],bin_minute=bin_start,
                                   source_minutes=int(mask.sum()),complete=bool(mask.sum()==15),volume=int(v[mask].sum()),
                                   range_points=float(h[mask].max()-l[mask].min()),
                                   absolute_close_change=float(np.abs(np.diff(c[indices])).sum())))
    flush(year)
    summary=dict(dataset_id=DATASET_ID,version='1.0.0',rows=total_rows,sessions=len(bounds)-1,
                 coverage_start=datetime.fromtimestamp(int(ts[0])/1e9,timezone.utc).isoformat(),
                 coverage_end=datetime.fromtimestamp(int(ts[-1])/1e9,timezone.utc).isoformat(),
                 output_files=files,source_integrity=integrity,compiler=compiler,
                 indicator_source={'path':f'catalog/indicators/{DATASET_ID}.source.pine','sha256':SOURCE_SHA},
                 point_in_time_certified=False,timestamp_units='UTC nanoseconds',price_units='NQ points',
                 snapshot_semantics='before signal minute; current bar OHLCV are observations, not causal features',
                 weekly_boundary='Monday trading date, Sunday 18:00 New York; exchange-session inference, not independently TradingView-feed certified',
                 retention='Published immutable partitions; no forward labels',
                 limitations=['OHLCV uniform-row approximation; no tick-profile or transient intraminute selection.',
                              'Historical last-bar gate replaced by sequential completed-minute replay.',
                              'Final adjusted snapshot is retrospective; raw execution prices retained.',
                              'Strict reference completeness uses normal sessions and flags holidays/early closes as incomplete; no bars filled.',
                              'Source volume-leader choice is a saved historical mapping, not a certified live roll rule.',
                              'Equal-strength suppression uses lower candidate order; Pine sort-indices tie stability not externally certified.'])
    summary['code']=[{'path':str(p.relative_to(workspace)),'sha256':sha256(p)} for p in sorted((workspace/'packages/bhishma/src/abacus_bhishma').glob('vp_hvn*')) if p.is_file()]
    summary['feature_protocol']={'path':f'catalog/indicators/{DATASET_ID}.spec.json','sha256':sha256(root/f'catalog/indicators/{DATASET_ID}.spec.json')}
    summary['request']={'path':f'requests/inbox/{DATASET_ID}.yaml','sha256':sha256(workspace/f'requests/inbox/{DATASET_ID}.yaml')}
    dump(stage/'build.json',summary)
    return summary


def validate_stage(stage):
    summary=json.loads((stage/'build.json').read_text())
    counts={'snapshots':0,'candidates':0,'decisions':0,'sessions':0,'rhythm':0}
    for record in summary['output_files']:
        p=stage/record['path']
        if sha256(p)!=record['sha256']:raise ValueError(f'stage hash changed: {p}')
        file=pq.ParquetFile(p)
        if file.metadata.num_rows!=record['rows']:raise ValueError('stage row count')
        counts[record['table']]+=record['rows']
        if record['table']=='snapshots':
            for batch in file.iter_batches(columns=['ts_event','available_at','rebuild_at','selected','adj_selected','post_selected']):
                for r in batch.to_pylist():
                    if r['available_at']>r['ts_event'] or (r['rebuild_at'] is not None and r['rebuild_at']>r['ts_event']):
                        raise ValueError('future pre-bar information')
                    for label in ('selected','adj_selected','post_selected'):
                        cutoff=r['ts_event']+(MINUTE if label=='post_selected' else 0)
                        for n in r[label]:
                            if n['available_at']>cutoff or n['hi']-n['lo']>2+1e-10:
                                raise ValueError('invalid selected node timing/bounds')
                        if any(sum(n['side']==side for n in r[label])>2 for side in (-1,1)):
                            raise ValueError('selected side quota')
        elif record['table']=='candidates':
            for batch in file.iter_batches(columns=['mass','input_volume','hi','lo','profile_rows']):
                q=batch.to_pydict()
                if not np.allclose(q['mass'],q['input_volume'],rtol=1e-10,atol=1e-6):raise ValueError('candidate volume mass')
                if np.any(np.array(q['hi'])-np.array(q['lo'])>2+1e-10) or np.any(np.array(q['profile_rows'])>3000):raise ValueError('candidate bounds/cap')
    if counts['snapshots']!=summary['rows'] or counts['decisions']!=counts['snapshots'] or counts['sessions']!=summary['sessions']:
        raise ValueError('release counts')
    result={'status':'pass','row_counts':counts,'study_outcomes_computed':False,'full_partition_hashes_checked':len(summary['output_files'])}
    dump(stage/'validation.json',result)
    return result


def publish(root,workspace,verified_stage=None):
    target=root/'data/features/vp_hvn'/f'version=1.0.0'
    catalog=root/f'catalog/datasets/{DATASET_ID}.json'
    stage=workspace/'work/bhishma'/DATASET_ID
    if target.exists() or catalog.exists() or (stage.exists() and verified_stage is None):raise FileExistsError('never overwrite a feature release')
    if verified_stage is None:
        summary=build(root,workspace,stage)
    else:
        stage=verified_stage.resolve()
        summary=json.loads((stage/'build.json').read_text())
    for r in summary['code']+[summary['request']]:
        if sha256(workspace/r['path'])!=r['sha256']:raise ValueError('builder/request changed after staged build')
    if sha256(root/summary['feature_protocol']['path'])!=summary['feature_protocol']['sha256']:
        raise ValueError('feature contract changed after staged build')
    verify_inputs(root,workspace)
    summary['validation']=validate_stage(stage)
    # Preserve actual dirty source bytes and contracts, not only their hashes.
    provenance=[]
    sources=[(workspace,r) for r in summary['code']+[summary['request']]]
    sources += [(root,r) for r in (summary['feature_protocol'],summary['indicator_source'])]
    sources += [(workspace,{'path':'uv.lock','sha256':sha256(workspace/'uv.lock')})]
    for base,r in sources:
        copy=stage/'provenance'/r['path'];copy.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(base/r['path'],copy)
        provenance.append({'path':str(copy.relative_to(stage)),'sha256':sha256(copy)})
    summary['provenance_files']=provenance
    summary['output_files']=[dict(x,path=str((target/x['path']).relative_to(root))) for x in summary['output_files']]
    target.parent.mkdir(parents=True,exist_ok=True);stage.rename(target)
    dump(catalog,summary)
    dump(root/f'catalog/indicators/{DATASET_ID}.json',{'dataset_id':DATASET_ID,'source':summary['indicator_source'],
         'main_profile':'Absolute 16-tick grid; first maximum POC; VA upper-adjacent tie; 70%; lower price coordinates.',
         'hvn':'10 completed + developing; low-anchored 4-tick grid, adaptive cap 3000; 3 smoothing, 20% peaks, +/-5, 10% prominence, 60% expansion, 8-tick bands/gaps; filter, strength, nearest, quotas.',
         'historical_adaptation':summary['snapshot_semantics'],'weekly_boundary':summary['weekly_boundary']})
    dump(root/f'catalog/schemas/{DATASET_ID}.json',{'dataset_id':DATASET_ID,'snapshots':str(SNAPSHOT),'decisions':str(DECISIONS),'table_files':summary['output_files'],'null_semantics':'NaN unavailable numerical level; null rebuild before first completed minute; never false-fill undefined events'})
    (root/f'reports/quality/{DATASET_ID}.md').write_text(f'# NQ causal VP/HVN 1.0.0\n\n{summary["rows"]:,} evening snapshots; {summary["sessions"]:,} observed dates. Full source/lineage hashes and OHLC/tick/order checks passed. Feature-only validation and source bytes are retained with the release. No trade labels or outcomes are included.\n\n'+ '\n'.join('- '+x for x in summary['limitations'])+'\n')
    shutil.copyfile(workspace/f'requests/inbox/{DATASET_ID}.yaml',workspace/f'requests/fulfilled/{DATASET_ID}.yaml')
    return catalog


def load_release(root, version, table='snapshots'):
    if version != '1.0.0':raise ValueError('explicit supported version required')
    manifest=json.loads((Path(root)/f'catalog/datasets/nq_causal_vp_hvn__{version}.json').read_text())
    files=[str(Path(root)/x['path']) for x in manifest['output_files'] if x['table']==table]
    return ds.dataset(files,format='parquet')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace',type=Path,default=Path.cwd())
    parser.add_argument('--root',type=Path)
    parser.add_argument('--pilot',type=Path)
    parser.add_argument('--publish-stage',type=Path)
    parser.add_argument('--start');parser.add_argument('--end')
    args=parser.parse_args();workspace=args.workspace.resolve();root=resolve_publication_root(args.root,workspace=workspace)
    if args.pilot:print(build(root,workspace,args.pilot,args.start,args.end)['rows'])
    else:print(publish(root,workspace,args.publish_stage))


if __name__=='__main__':main()
