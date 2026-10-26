"""Execute frozen Asia VP study from the pinned causal feature release."""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
import gzip
import html
import importlib.metadata
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from abacus_bhishma.paths import load_workspace_paths
from abacus_bhishma.provenance import sha256_file as sha256
from .evidence import dump, PACKAGE_SOURCE_PATHS
from .execution import HORIZONS, MINUTE_NS, _strict, session_signals, session_outcomes
from .outcomes import excursion, race
from .statistics import development_quintiles, volatility_bin, moving_week_mean_interval, support

STUDY = '14_asia_session_vp_levels'
RELEASE = 'nq_causal_vp_hvn__1.0.0'


def split(year):
    if year <= 2019: return 'historical'
    if year <= 2023: return 'development'
    if year <= 2025: return 'validation'
    return 'final_2026_ytd'


def json_ready(value):
    if isinstance(value, dict): return {str(k): json_ready(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)): return [json_ready(v) for v in value]
    if isinstance(value, (np.integer,)): return int(value)
    if isinstance(value, (np.floating,)): value = float(value)
    if isinstance(value, (np.bool_,)): return bool(value)
    if isinstance(value, float) and not math.isfinite(value): return None
    return value


def write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, 'wt', encoding='utf-8') as stream:
        for row in rows:
            stream.write(json.dumps(json_ready(row), sort_keys=True, separators=(',', ':'), allow_nan=False)+'\n')


def read_snapshots(root, manifest, year):
    item = next(x for x in manifest['output_files'] if x['table'] == 'snapshots' and x['year'] == year)
    return pq.read_table(root/item['path']).to_pylist()


def session_groups(records):
    group, key = [], None
    for record in records:
        if record['session_date'] != key:
            if group: yield key, group
            group, key = [], record['session_date']
        group.append(record)
    if group: yield key, group


def _eligible_control_pool(sessions, cutoffs):
    pool = defaultdict(list)
    for session_date, records in sessions.items():
        n = len(records)
        for i, r in enumerate(records):
            minute = int(r['minute'])
            if not 120 <= minute <= 329 or i+30 >= n or not math.isfinite(r['volatility60']):
                continue
            entry = records[i+1]
            last = records[i+30]
            if (entry['ts_event'] != r['ts_event']+MINUTE_NS
                    or last['ts_event'] != entry['ts_event']+29*MINUTE_NS):
                continue
            if any(x['raw_symbol'] != r['raw_symbol'] or x['roll_id'] != r['roll_id']
                   or x['source_degraded'] for x in records[i+1:i+31]):
                continue
            vol_bin = int(volatility_bin([r['volatility60']], cutoffs)[0])
            hour = 18+minute//60
            for setup in ('A', 'B', 'C'):
                if _strict(r, setup):
                    pool[(setup, hour, vol_bin)].append((session_date, i))
    return pool


def _control_outcome(records, i, direction):
    path = records[i+1:i+31]
    o = np.array([x['open'] for x in path]); hi=np.array([x['high'] for x in path])
    lo=np.array([x['low'] for x in path]); c=np.array([x['close'] for x in path])
    return excursion(o,hi,lo,c,direction,records[i]['volatility60'])


def _flat_outcome(r):
    fields=('setup','variant','direction','session_date','year','week','season','minute','hour',
            'signal_ts','entry_ts','entry','level','origin_minute','pre_20_origin','node_id','node_rank',
            'volatility60','va_width','entry_distance_points','near_entry_2_points',
            'horizon','horizon_label','holding_minutes','path_status',
            'mae_points','mfe_points','terminal_points','mae_ticks','mfe_ticks','terminal_ticks',
            'mae_dollars','mfe_dollars','terminal_dollars','mae_tr60','mfe_tr60','terminal_tr60',
            'mae_va_width','mfe_va_width','terminal_va_width','terminal_positive',
            'rejection_confirmed','post_selected')
    return {k:r.get(k) for k in fields}


def _interval(frame, metric, block=2):
    if frame.empty: return {'estimate':None,'lower':None,'upper':None,'events':0,'weeks':0}
    return moving_week_mean_interval(frame.week.to_numpy(dtype='datetime64[D]'),
                                     frame[metric].to_numpy(dtype=float),block=block)


def _summarize(frame):
    rows=[]
    keys=('split','setup','variant','direction','horizon')
    for key, group in frame.groupby(list(keys), dropna=False, sort=True):
        complete=group[group.path_status=='complete']
        row=dict(zip(keys,key))
        row.update(events=len(group),complete=len(complete),censored=len(group)-len(complete),
                   sessions=complete.session_date.nunique(),weeks=complete.week.nunique())
        row['support']=support(len(complete),row['sessions'],row['weeks'])
        for metric in ('mfe_points','mae_points','terminal_points'):
            v=complete[metric].dropna().to_numpy(dtype=float)
            row[metric+'_mean']=float(v.mean()) if len(v) else None
            for name,q in (('median',.5),('p25',.25),('p75',.75),('p90',.9),('p95',.95)):
                row[metric+'_'+name]=float(np.quantile(v,q)) if len(v) else None
            ci=_interval(complete,metric)
            row[metric+'_ci_lower']=ci.get('lower'); row[metric+'_ci_upper']=ci.get('upper')
        row['terminal_positive_share']=float(complete.terminal_positive.mean()) if len(complete) else None
        rows.append(row)
    return pd.DataFrame(rows)


def _summarize_races(accumulator):
    rows=[]
    for key, stat in sorted(accumulator.items()):
        n=stat['events']
        rows.append(dict(zip(('split','setup','variant','direction','horizon','threshold'),key))|
                    {'events':n,'favorable_first_lower':stat['lower']/n,
                     'favorable_first_upper':stat['upper']/n,'adverse_first':stat['adverse'],
                     'ambiguous':stat['ambiguous'],'neither':stat['neither'],
                     'target_non_hit':stat['non_hit'],
                     'pre_target_mae_lower_median':float(np.median(stat['pre_lower'])) if stat['pre_lower'] else None,
                     'pre_target_mae_upper_median':float(np.median(stat['pre_upper'])) if stat['pre_upper'] else None})
    return pd.DataFrame(rows)


def _add_race(accumulator, outcome, threshold, rr):
    key=(split(outcome['year']),outcome['setup'],outcome['variant'],outcome['direction'],outcome['horizon'],threshold)
    stat=accumulator.setdefault(key,{'events':0,'lower':0,'upper':0,'adverse':0,'ambiguous':0,
                                     'neither':0,'non_hit':0,'pre_lower':[],'pre_upper':[]})
    stat['events']+=1;stat['lower']+=rr['favorable_first_lower'];stat['upper']+=rr['favorable_first_upper']
    status=rr['status']
    if status.startswith('adverse_first'):stat['adverse']+=1
    if status=='same_bar_ambiguous':stat['ambiguous']+=1
    if status=='neither':stat['neither']+=1
    stat['non_hit']+=int(rr['non_hit'])
    if rr['pre_target_mae_lower'] is not None:stat['pre_lower'].append(rr['pre_target_mae_lower'])
    if rr['pre_target_mae_upper'] is not None:stat['pre_upper'].append(rr['pre_target_mae_upper'])


def _match_controls(primary, year, sessions, pool, cutoffs):
    rng=np.random.default_rng(1414+year)
    records=[]
    for event in primary:
        bin_=int(volatility_bin([event['volatility60']],cutoffs)[0])
        options=pool.get((event['setup'],event['hour'],bin_),[])
        own=(event['session_date'],next((i for i,r in enumerate(sessions[event['session_date']]) if r['ts_event']==event['signal_ts']),-1))
        support_count=len(options)-int(own in options)
        row={'setup':event['setup'],'direction':event['direction'],'year':year,'split':split(year),
             'session_date':event['session_date'],'week':event['week'],'hour':event['hour'],
             'volatility_bin':bin_,'event_signal_ts':event['signal_ts'],'pool_support':support_count,
             'event_volatility60':event['volatility60'],
             'event_mfe':event['mfe_points'],'event_mae':event['mae_points'],
             'event_terminal':event['terminal_points']}
        if support_count:
            choice=int(rng.integers(len(options)))
            if options[choice]==own: choice=(choice+1)%len(options)
            date,i=options[choice]; r=sessions[date][i]
            control=_control_outcome(sessions[date],i,event['direction'])
            row.update(control_session_date=date,control_ts=r['ts_event'],
                       control_volatility60=r['volatility60'],control_mfe=control['mfe_points'],
                       control_mae=control['mae_points'],control_terminal=control['terminal_points'],
                       difference_mfe=event['mfe_points']-control['mfe_points'],
                       difference_mae=event['mae_points']-control['mae_points'],
                       difference_terminal=event['terminal_points']-control['terminal_points'])
        records.append(row)
    return records


def _markdown_table(frame, max_rows=100):
    if frame.empty: return '_No rows._\n'
    f=frame.head(max_rows).copy()
    for col in f.columns:
        if pd.api.types.is_numeric_dtype(f[col]):
            f[col]=f[col].map(lambda x: '' if pd.isna(x) else (f'{x:.3f}' if isinstance(x,float) else str(x)))
    columns=list(f.columns)
    def cell(value):
        return str(value).replace('|','/').replace('\n',' ')
    header='| '+' | '.join(columns)+' |\n'
    divider='| '+' | '.join('---' for _ in columns)+' |\n'
    body=''.join('| '+' | '.join(cell(x) for x in row)+' |\n'
                 for row in f.itertuples(index=False,name=None))
    return header+divider+body


def _render_saved(stage):
    metrics=pd.read_csv(stage/'tables/metrics.csv')
    funnel=pd.read_csv(stage/'tables/funnel.csv')
    controls=pd.read_csv(stage/'tables/control_effects.csv')
    races=pd.read_csv(stage/'tables/races.csv')
    quality=pd.read_csv(stage/'tables/quality_by_year.csv') if (stage/'tables/quality_by_year.csv').exists() else pd.DataFrame()
    sensitivity=pd.read_csv(stage/'tables/sensitivity_comparison_30m.csv') if (stage/'tables/sensitivity_comparison_30m.csv').exists() else pd.DataFrame()
    primary=metrics[(metrics.horizon==30)&(metrics.variant=='primary')]
    view=primary[['split','setup','direction','complete','mfe_points_median','mae_points_median',
                  'terminal_points_mean','terminal_positive_share','support']]
    control_view=controls[['split','setup','direction','events','matched','mfe_difference_mean',
                           'mfe_ci_lower','mfe_ci_upper','mae_difference_mean','mae_ci_lower','mae_ci_upper',
                           'terminal_difference_mean','terminal_ci_lower','terminal_ci_upper']]
    race_view=races[(races.horizon==30)&(races.threshold=='1x_tr60')&
                    (races.variant=='primary')][['split','setup','direction','events',
                    'favorable_first_lower','favorable_first_upper','ambiguous','neither']]
    n=primary.complete.sum()
    intro=(f'# Asia session VP levels — NQ one-minute study\n\n'
           f'Frozen protocol 1.0.0. Setup A is **long at POC after an upper VAH excursion** and '
           f'**short at POC after a lower VAL excursion**, as confirmed by the user. '
           f'The primary 30-minute complete cohort has {n:,} setup/horizon records across sides and splits. '
           'These are hypothetical next-open excursions, not realized trades.\n\n')
    methods=('Primary inputs are pre-signal unadjusted feature snapshots; the indicator release is pinned. '
             'Every complete fixed horizon uses contiguous minute bars, the actual next open, and entry candle OHLC. '
             'Incomplete futures paths and unavailable causal features are explicit exclusions. '
             'Two-week moving ISO-week blocks (2,000 draws) express uncertainty. '
             'Matched controls share year, side, New York hour and development-defined pre-signal volatility quintile. '
             'One-minute OHLCV does not reveal bid/ask, queue position, exact intrabar ordering, or TradingView tick parity. '
             'Same-bar threshold ordering is bounded. No net-profit or strategy claim is made.\n\n')
    validation=control_view[control_view['split']=='validation']
    def val(setup,direction):
        result=validation[(validation.setup==setup)&(validation.direction==direction)]
        return result.iloc[0] if len(result) else None
    a_long,a_short=val('A',1),val('A',-1)
    b_long,b_short=val('B',1),val('B',-1)
    c_long,c_short=val('C',1),val('C',-1)
    conclusions=[]
    if a_long is not None and a_short is not None:
        conclusions.append('- Setup A, POC-entry fade: validation does not establish an excess favorable excursion on either side. '
            f'The long matched-MFE difference is {a_long.mfe_difference_mean:+.2f} points '
            f'[{a_long.mfe_ci_lower:+.2f}, {a_long.mfe_ci_upper:+.2f}]; '
            f'the short difference is {a_short.mfe_difference_mean:+.2f} '
            f'[{a_short.mfe_ci_lower:+.2f}, {a_short.mfe_ci_upper:+.2f}]. '
            'Both intervals span zero; this hypothesis remains inconclusive as an advantage.')
    if b_long is not None and b_short is not None:
        conclusions.append('- Setup B, VAH/VAL breakout retest: validation shows a larger favorable excursion on the short side '
            f'({b_short.mfe_difference_mean:+.2f} points, interval '
            f'[{b_short.mfe_ci_lower:+.2f}, {b_short.mfe_ci_upper:+.2f}]). '
            f'The long estimate is {b_long.mfe_difference_mean:+.2f} '
            f'[{b_long.mfe_ci_lower:+.2f}, {b_long.mfe_ci_upper:+.2f}]. '
            'This is partial descriptive support for short-side movement, not a demonstrated two-sided or net-trading edge.')
    if c_long is not None and c_short is not None:
        conclusions.append('- Setup C, selected HVN fade: favorable-excursion differences remain uncertain on both validation sides. '
            f'Short-side adverse excursion is higher than matched minutes by {c_short.mae_difference_mean:+.2f} points '
            f'[{c_short.mae_ci_lower:+.2f}, {c_short.mae_ci_upper:+.2f}], evidence against the short fade’s risk premise. '
            'The long side remains inconclusive.')
    if quality.empty:
        quality_text=''
        quality_html=''
    else:
        quality_view=quality[['year','complete_six_hour_evenings','strict_overnight_input','strict_hvn_reference_input']]
        quality_text=('\n## Input quality and historical coverage\n\n'+_markdown_table(quality_view)+
            '\nStrict six-hour input coverage is sparse before 2018; early historical estimates have materially weaker support. '
            'The full source-quality ledger is in `tables/quality_by_year.csv`.\n')
        quality_html='<h2>Input quality by year</h2><div class="scroll">'+quality_view.to_html(index=False,escape=True,border=0)+'</div><p>Strict coverage is sparse before 2018.</p>'
    if sensitivity.empty:
        sensitivity_text='';sensitivity_html=''
    else:
        sensitivity_view=sensitivity[sensitivity['split']=='validation']
        sensitivity_text=('\n## Prespecified coordinate and frozen-level sensitivities\n\n'+_markdown_table(sensitivity_view)+
            '\nThese rows use different event cohorts, so differences in means are not paired effects. '
            'The adjusted-profile coordinate variant is retrospective and is not certified point in time. '
            'All hypothetical fills and excursions remain in actual unadjusted NQ prices. '
            'Other splits and horizons are in `tables/sensitivity_metrics.csv`.\n')
        sensitivity_html='<h2>Profile-coordinate and frozen-level checks</h2><div class="scroll">'+sensitivity_view.to_html(index=False,escape=True,border=0)+'</div><p>Adjusted-profile coordinates are retrospective; all outcomes use actual unadjusted prices. Cohorts differ.</p>'
    report=(intro+'## Primary 30-minute paths\n\n'+_markdown_table(view)+
        '\n## Matched-minute differences (event minus control, NQ points)\n\n'+_markdown_table(control_view)+
        '\n## First-passage race, +1 versus −1 prior-60-minute true-range unit\n\n'+_markdown_table(race_view)+
        '\n## Conclusions\n\n'+'\n'.join(conclusions)+'\n'+quality_text+
        sensitivity_text+'\n## Fixed-rule representative paths\n\n![Positive, negative, ambiguous, and excluded examples with developing profile levels](figures/representative_profiles.svg)\n\n'
        'The positive/negative labels use the 30-minute terminal move. The excluded example has no trade outcome and is anchored to its signal close. '
        'The selected examples are the first chronological match in each setup and class.\n\n'
        '## Methods and limits\n\n'+methods+
        'Saved evidence includes all horizon rows, year and side tables, signal and exclusion ledgers, threshold races, and representative paths. '
        'Historical 2010–2019 is context; 2020–2023 is development; 2024–2025 is validation; 2026 is YTD final check. '
        'The report is local and offline; it has not been published to the web.\n')
    (stage/'report.md').write_text(report)
    (stage/'advice.md').write_text('# Dated interpretation — '+datetime.now(timezone.utc).date().isoformat()+
        '\n\n'+'\n'.join(conclusions)+'\n\nThe tables measure hypothetical excursions and matched behavior, not executable net returns. '
        'Do not promote these patterns to a strategy without independent fill, cost, and out-of-sample execution research.\n')
    table_html=view.to_html(index=False,escape=True,border=0)
    controls_html=control_view.to_html(index=False,escape=True,border=0)
    race_html=race_view.to_html(index=False,escape=True,border=0)
    page=f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Asia session VP levels — NQ</title>
<style>body{{font:16px/1.55 system-ui;background:#f5f7fa;color:#173144;max-width:1260px;margin:42px auto;padding:0 24px}}h1{{font-size:36px}}.lede{{background:#e8f0fb;padding:18px;border-left:5px solid #3477b4}}.scroll{{overflow:auto}}table{{border-collapse:collapse;background:white;font-size:13px}}td,th{{padding:8px;border-bottom:1px solid #dde4eb;text-align:right}}th:first-child,td:first-child{{text-align:left}}p{{max-width:960px}}</style>
<h1>Asia session VP levels</h1><p class="lede">{html.escape(intro.splitlines()[2])}</p>
<h2>30-minute paths</h2><div class="scroll">{table_html}</div>
<h2>Matched-minute differences</h2><div class="scroll">{controls_html}</div>
<h2>Threshold race</h2><div class="scroll">{race_html}</div>
<h2>Conclusions</h2><ul>{''.join('<li>'+html.escape(c[2:])+'</li>' for c in conclusions)}</ul>
{quality_html}
{sensitivity_html}
<h2>Fixed-rule representative paths</h2><img src="figures/representative_profiles.svg" width="100%" alt="Positive, negative, ambiguous and excluded examples with changing POC and value edges"><p>The excluded example has no trade outcome; it is anchored to signal close.</p>
<h2>Methods and limits</h2><p>{html.escape(methods)}</p>
<p><a href="report.md">Full Markdown report</a> · <a href="tables/metrics.csv">Metrics</a> · <a href="tables/funnel.csv">Opportunity funnel</a> · <a href="tables/control_effects.csv">Controls</a> · <a href="tables/races.csv">Races</a></p></html>'''
    (stage/'report.html').write_text(page)


def execute(stage):
    paths=load_workspace_paths(); root=paths.publication_root; workspace=paths.workspace_root
    study=workspace/'studies'/STUDY
    settings_text=(study/'study.yaml').read_text()
    if ('protocol_status: frozen_before_outcomes' not in settings_text
            or 'primary: poc_entry_fade_of_return_leg' not in settings_text):
        raise ValueError('frozen POC-entry protocol required')
    lock=json.loads((study/'inputs.lock.json').read_text())
    identity=lock['derived_feature_release']; manifest_file=root/identity['manifest_path']
    if sha256(manifest_file)!=identity['sha256']: raise ValueError('feature manifest hash mismatch')
    manifest=json.loads(manifest_file.read_text())
    for item in manifest['output_files']:
        if sha256(root/item['path'])!=item['sha256']:
            raise ValueError(f"feature file changed: {item['path']}")
    if not (study/'protocol-1.0.0.md').is_file(): raise ValueError('frozen study protocol missing')
    stage=stage.resolve(); stage.mkdir(parents=True,exist_ok=False)
    for name in ('tables','events','source','figures'): (stage/name).mkdir()
    dev=[]
    for year in range(2020,2024):
        item=next(x for x in manifest['output_files'] if x['table']=='snapshots' and x['year']==year)
        table=pq.read_table(root/item['path'],columns=['minute','volatility60','overnight_complete','overnight_contract_clean','source_degraded'])
        for r in table.to_pylist():
            if 120<=r['minute']<=329 and r['overnight_complete'] and r['overnight_contract_clean'] and not r['source_degraded']:
                dev.append(r['volatility60'])
    cutoffs=np.quantile(np.asarray([v for v in dev if math.isfinite(v)]),[.2,.4,.6,.8])
    del dev
    all_flat=[]; race_acc={}; all_ledger=[]; all_controls=[]; examples=[]
    path_acc=defaultdict(list); structural_acc=defaultdict(Counter)
    for year in range(2010,2027):
        records=read_snapshots(root,manifest,year)
        sessions=dict(session_groups(records))
        year_ledger=[]; year_signals=[]; year_outcomes=[]
        for session_date, group in sessions.items():
            ledger,signals=session_signals(group)
            year_ledger.extend(ledger)
            year_signals.extend(signals)
            year_outcomes.extend(session_outcomes(group,signals))
        write_jsonl(stage/f'events/ledger_{year}.jsonl.gz',year_ledger)
        write_jsonl(stage/f'events/signals_{year}.jsonl.gz',year_signals)
        write_jsonl(stage/f'events/outcomes_{year}.jsonl.gz',year_outcomes)
        all_ledger.extend(year_ledger)
        for r in year_outcomes:
            flat=_flat_outcome(r); flat['split']=split(year);all_flat.append(flat)
            if r['path_status']=='complete':
                if r['horizon']==30 and r['variant']=='primary':
                    examples.append({'setup':r['setup'],'direction':r['direction'],'session_date':r['session_date'],
                                     'signal_ts':r['signal_ts'],'terminal_points':r['terminal_points'],
                                     'mfe_points':r['mfe_points'],'mae_points':r['mae_points'],
                                     'signed_path':r['signed_path'],'race_status':None if r['race_tr60'] is None else r['race_tr60']['status']})
                    path_acc[(split(year),r['setup'],r['direction'])].append(r['signed_path'])
                    structural_acc[(split(year),r['setup'],r['direction'])]['events']+=1
                    ref=r['reference_hit']
                    structural_acc[(split(year),r['setup'],r['direction'])]['reference_defined']+=int(ref['defined'])
                    structural_acc[(split(year),r['setup'],r['direction'])]['reference_ahead']+=int(bool(ref['ahead']))
                    structural_acc[(split(year),r['setup'],r['direction'])]['reference_range_hit']+=int(bool(ref['range_hit']))
                    structural_acc[(split(year),r['setup'],r['direction'])]['reference_directional_reach']+=int(bool(ref['directional_reach']))
                for distance in (2,4,8,12,20):
                    rr=r.get(f'race_{distance}pt')
                    if rr:_add_race(race_acc,r,f'{distance}pt',rr)
                if r['horizon']==30 and r.get('race_tr60'):
                    _add_race(race_acc,r,'1x_tr60',r['race_tr60'])
        primary=[r for r in year_outcomes if r['horizon']==30 and r['variant']=='primary' and r['path_status']=='complete']
        pool=_eligible_control_pool(sessions,cutoffs)
        all_controls.extend(_match_controls(primary,year,sessions,pool,cutoffs))
        print(f'{year}: {len(year_signals)} signals; {len(primary)} complete primary 30m paths',flush=True)
        del records,sessions,year_ledger,year_signals,year_outcomes,pool
    flat=pd.DataFrame(all_flat)
    flat.to_csv(stage/'tables/outcomes.csv',index=False)
    metrics=_summarize(flat)
    metrics.to_csv(stage/'tables/metrics.csv',index=False)
    primary=flat[(flat.variant=='primary')&(flat.horizon==30)&(flat.path_status=='complete')].copy()
    yearly=primary.groupby(['year','split','setup','direction']).agg(
        events=('entry','size'),sessions=('session_date','nunique'),weeks=('week','nunique'),
        mfe_mean=('mfe_points','mean'),mfe_median=('mfe_points','median'),
        mae_mean=('mae_points','mean'),mae_median=('mae_points','median'),
        terminal_mean=('terminal_points','mean'),terminal_positive_share=('terminal_positive','mean')).reset_index()
    yearly.to_csv(stage/'tables/yearly_primary.csv',index=False)
    hourly=primary.groupby(['split','setup','direction','hour','season']).agg(
        events=('entry','size'),sessions=('session_date','nunique'),
        mfe_mean=('mfe_points','mean'),mae_mean=('mae_points','mean'),
        terminal_mean=('terminal_points','mean')).reset_index()
    hourly.to_csv(stage/'tables/hour_season_primary.csv',index=False)
    context=primary.groupby(['split','setup','direction','near_entry_2_points','pre_20_origin','node_rank'],
                            dropna=False).agg(events=('entry','size'),mfe_mean=('mfe_points','mean'),
                                mae_mean=('mae_points','mean'),terminal_mean=('terminal_points','mean')).reset_index()
    context.to_csv(stage/'tables/context_primary.csv',index=False)
    path_rows=[]
    for key,paths_ in sorted(path_acc.items()):
        array=np.asarray(paths_,dtype=float)
        for i,value in enumerate(np.median(array,axis=0)):
            path_rows.append(dict(zip(('split','setup','direction'),key))|
                             {'minute_after_entry':i,'median_signed_close_points':float(value),'events':len(array)})
    pd.DataFrame(path_rows).to_csv(stage/'tables/median_signed_paths.csv',index=False)
    pd.DataFrame([dict(zip(('split','setup','direction'),key))|dict(counts)
                  for key,counts in sorted(structural_acc.items())]).to_csv(stage/'tables/structural_hits.csv',index=False)
    robustness=[]
    for key,g in flat[(flat.horizon==30)&(flat.path_status=='complete')].groupby(
            ['split','setup','direction','variant','near_entry_2_points'],dropna=False):
        robustness.append(dict(zip(('split','setup','direction','variant','near_entry_2_points'),key))|
                          {'events':len(g),'sessions':g.session_date.nunique(),
                           'mfe_mean':g.mfe_points.mean(),'mae_mean':g.mae_points.mean(),
                           'terminal_mean':g.terminal_points.mean()})
    pd.DataFrame(robustness).to_csv(stage/'tables/robustness.csv',index=False)
    sensitivity=[]
    for key,g in primary.groupby(['split','setup','direction']):
        four=_interval(g,'mfe_points',block=4)
        per_session=g.groupby('session_date')[['mfe_points','mae_points','terminal_points']].mean()
        sensitivity.append(dict(zip(('split','setup','direction'),key))|
                           {'events':len(g),'mfe_4week_ci_lower':four.get('lower'),
                            'mfe_4week_ci_upper':four.get('upper'),
                            'session_weight_mfe_mean':per_session.mfe_points.mean(),
                            'session_weight_mae_mean':per_session.mae_points.mean(),
                            'session_weight_terminal_mean':per_session.terminal_points.mean()})
    pd.DataFrame(sensitivity).to_csv(stage/'tables/sensitivity.csv',index=False)
    leave=[]
    for setup in ('A','B','C'):
        for direction in (-1,1):
            group=primary[(primary.setup==setup)&(primary.direction==direction)]
            for year in sorted(group.year.unique()):
                subset=group[group.year!=year]
                leave.append({'setup':setup,'direction':direction,'left_out_year':int(year),
                              'events':len(subset),'mfe_mean':subset.mfe_points.mean(),
                              'mae_mean':subset.mae_points.mean(),
                              'terminal_mean':subset.terminal_points.mean()})
    pd.DataFrame(leave).to_csv(stage/'tables/leave_one_year_out.csv',index=False)
    funnel=pd.DataFrame(all_ledger).groupby(['year','setup','direction','status'],dropna=False).size().rename('count').reset_index()
    funnel.to_csv(stage/'tables/funnel.csv',index=False)
    races=_summarize_races(race_acc);races.to_csv(stage/'tables/races.csv',index=False)
    controls=pd.DataFrame(all_controls);controls.to_csv(stage/'tables/matched_controls.csv',index=False)
    effect=[]
    for key,g in controls.groupby(['split','setup','direction'],sort=True):
        matched=g[g.difference_mfe.notna()]
        row=dict(zip(('split','setup','direction'),key))
        row.update(events=len(g),matched=len(matched),unmatched=len(g)-len(matched),
                   median_pool_support=g.pool_support.median(),
                   event_volatility_mean=g.event_volatility60.mean(),
                   matched_control_volatility_mean=matched.control_volatility60.mean())
        for metric in ('mfe','mae','terminal'):
            name=f'difference_{metric}';ci=_interval(matched.rename(columns={name:'difference'}),'difference')
            row[f'{metric}_difference_mean']=ci['estimate']
            row[f'{metric}_ci_lower']=ci.get('lower');row[f'{metric}_ci_upper']=ci.get('upper')
        effect.append(row)
    effects=pd.DataFrame(effect);effects.to_csv(stage/'tables/control_effects.csv',index=False)
    # One deterministic representative from each outcome class; no attractive-only cherry-picking.
    chosen=[]
    for setup in ('A','B','C'):
        items=[e for e in examples if e['setup']==setup]
        for label,predicate in (('positive',lambda e:e['terminal_points']>0),
                                ('negative',lambda e:e['terminal_points']<=0),
                                ('ambiguous',lambda e:e['race_status']=='same_bar_ambiguous')):
            found=next((e for e in sorted(items,key=lambda x:(x['session_date'],x['signal_ts'])) if predicate(e)),None)
            if found: chosen.append({'class':label,**found})
    write_jsonl(stage/'tables/representative_paths.jsonl.gz',chosen)
    dump(stage/'metrics.json',{'study_id':STUDY,'protocol_version':'1.0.0','primary_horizon':30,
        'signal_rows':len(all_ledger),'outcome_rows':len(flat),'control_rows':len(controls),
        'development_volatility_quintiles':cutoffs.tolist(),
        'feature_manifest_sha256':identity['sha256'],
        'primary_summary':metrics[(metrics.horizon==30)&(metrics.variant=='primary')].to_dict('records')})
    dump(stage/'config.json',{'format':'frozen study.yaml verbatim','study_yaml':settings_text})
    shutil.copyfile(study/'inputs.lock.json',stage/'inputs.lock.json')
    _render_saved(stage)
    sources=[study/'study.yaml',study/'protocol-1.0.0.md',study/'inputs.lock.json',workspace/'uv.lock',
             *(workspace/path for path in PACKAGE_SOURCE_PATHS),
             *sorted((study/'src').glob('*.py')),*sorted((study/'tests').glob('*.py'))]
    source_records=[]
    for source in sources:
        dest=stage/'source'/source.relative_to(workspace);dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(source,dest)
        source_records.append({'path':str(source.relative_to(workspace)),'sha256':sha256(source)})
    artifacts=[{'path':str(p.relative_to(stage)),'sha256':sha256(p),'bytes':p.stat().st_size}
               for p in sorted(stage.rglob('*')) if p.is_file()]
    command=f'UV_CACHE_DIR=work/.uv-cache ./scripts/uv run --locked --no-sync python studies/{STUDY}/run.py --execute --stage {stage.relative_to(workspace)}'
    dump(stage/'manifest.json',{'study_id':STUDY,'run_id':stage.name,'created_utc':datetime.now(timezone.utc).isoformat(),
        'status':'staged_verified_pending_seal','command':command,'git_revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=workspace,text=True).strip(),
        'git_status':subprocess.check_output(['git','status','--porcelain'],cwd=workspace,text=True),
        'python':sys.version,'environment':{x:importlib.metadata.version(x) for x in ('numpy','pandas','pyarrow')},
        'uv_lock_sha256':sha256(workspace/'uv.lock'),'feature_manifest':identity,'protocol_sha256':sha256(study/'protocol-1.0.0.md'),
        'source_snapshot':source_records,'artifacts':artifacts,'checks':{'feature_hashes':'passed','source_signal_tests':'pending_final_verification'},
        'template_version':'abacus-report-1'})
    return stage


def augment_sensitivities(stage):
    """Add the prespecified adjusted-grid and frozen-breakout-level cohorts.

    Their executions still use actual unadjusted OHLC. This is a separate pass
    over immutable feature evidence; primary cohort files are never changed.
    """
    paths=load_workspace_paths();root=paths.publication_root
    stage=stage.resolve()
    if not (stage/'tables/metrics.csv').is_file(): raise ValueError('primary staged run required')
    manifest=json.loads((root/f'catalog/datasets/{RELEASE}.json').read_text())
    rows=[]
    for year in range(2010,2027):
        annual=[]
        for _,group in session_groups(read_snapshots(root,manifest,year)):
            adjusted=[dict(r,on_vah=r['adj_on_vah'],on_poc=r['adj_on_poc'],on_val=r['adj_on_val'],
                           selected=r['adj_selected'],post_selected=[]) for r in group]
            _, signals=session_signals(adjusted)
            primary=[dict(s,variant='adjusted_snapshot') for s in signals
                     if s['variant']=='primary' and s['status']=='accepted']
            annual.extend(session_outcomes(adjusted,primary))
            _, frozen_signals=session_signals(group,level_mode='frozen_breakout')
            frozen=[dict(s,variant='frozen_breakout_level') for s in frozen_signals
                    if s['setup'] in ('A','B') and s['variant']=='primary' and s['status']=='accepted']
            annual.extend(session_outcomes(group,frozen))
        write_jsonl(stage/f'events/sensitivity_outcomes_{year}.jsonl.gz',annual)
        for r in annual:
            item=_flat_outcome(r);item['split']=split(year);rows.append(item)
        print(f'{year}: {len(annual)} sensitivity horizon records',flush=True)
    frame=pd.DataFrame(rows)
    frame.to_csv(stage/'tables/sensitivity_outcomes.csv',index=False)
    metrics=_summarize(frame)
    metrics.to_csv(stage/'tables/sensitivity_metrics.csv',index=False)
    comparison=metrics[(metrics.horizon==30)][['split','setup','direction','variant','complete',
        'mfe_points_mean','mae_points_mean','terminal_points_mean']]
    comparison.to_csv(stage/'tables/sensitivity_comparison_30m.csv',index=False)
    return len(frame)
