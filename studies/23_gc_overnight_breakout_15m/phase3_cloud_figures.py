"""Saved empirical Phase3 cloud figures, with explicit vector/source identity.

Only the already-selected example JSON and named CSV projections are read.
Price scaling and SVG geometry are presentation transforms, not research metrics.
No engine, runner, metrics, exporter or independent checker is imported.
"""
from __future__ import annotations

from datetime import datetime,timezone
from html import escape
import json
import math
from phase2_publish_web import svg_start,svg_text,wrapped_svg,value_type

POLICIES={'ema20-support':('A20',),'ema50-support':('A50',),'earlier-exits':('X1','X2')}
COLORS={'close':'#244d43','ema20':'#885fb5','ema50':'#bd8b31'}


def clock(value):
    parsed=datetime.fromisoformat(value.replace('Z','+00:00'))
    if parsed.tzinfo is None:raise ValueError('saved empirical timestamp requires timezone')
    return parsed.astimezone(timezone.utc).timestamp()


def scalar(raw):
    if raw=='':return None
    value=float(raw)
    if not math.isfinite(value):raise ValueError('finite saved price')
    return value


def binding(draft,artifact,pointer):
    value=json.loads(draft.files[artifact])
    for key in pointer[1:].split('/'):
        key=key.replace('~1','/').replace('~0','~')
        value=value[int(key)] if isinstance(value,list) else value[key]
    return dict(source_artifact=artifact,source_pointer=pointer,value_type=value_type(value),original_stage_source_path=draft.sources[artifact]['original_stage_source_path'],original_source_pointer=pointer)


def csv_binding(draft,artifact,index,key,kind='string'):
    source=draft.sources[artifact]
    return dict(source_artifact=artifact,source_row=index,source_column=key,value_type=kind,original_stage_source_path=source['original_stage_source_path'],original_source_row=source['selected_source_rows'][index],original_source_column=key)


def token(value,display):
    if value is None:return 'Unavailable'
    if display['style']=='verbatim':return str(value).lower() if type(value) is bool else str(value)
    return format(value,(',' if display.get('grouping') else '')+'.'+str(display.get('precision',1))+'f')


def number(value):
    return format(value,'.6f')


def render_policy(draft,policy,selected):
    """One bounded figure from the source's balanced cases, without reselection."""
    case_art='example-selection.json'
    minutes=draft.copy_table('tables/selected-example-minutes.csv',f'tables/cloud-cases-{policy.lower()}-minutes.csv',{'case_id':tuple(case['id'] for _,case in selected)},['case_id','episode_id','contract','timestamp','available_at','open','high','low','close','usable'])
    cloud=draft.copy_table('tables/selected-example-cloud.csv',f'tables/cloud-cases-{policy.lower()}-cloud.csv',{'case_id':tuple(case['id'] for _,case in selected)},['case_id','episode_id','contract','timestamp','available_at','ema20','ema50','usable','feature_valid'])
    minute_rows=draft.copied_table(minutes);cloud_rows=draft.copied_table(cloud)
    width=1240;height=180+680*((len(selected)+1)//2)
    title=policy+' — earliest chronological balanced saved examples'
    subtitle='Unadjusted GC minute closes and confirmed 5m EMA20/50, at their available clocks. Per-panel price scale; missing cloud spans remain gaps. Modeled fill/exit markers include assumed adverse ticks.'
    svg=svg_start(width,height,title,subtitle)
    panels=[];timing=[]
    for panel_index,(case_index,case) in enumerate(selected):
        panel_id='case-'+case['id'];pointer='/cases/'+str(case_index)
        xleft=65+(panel_index%2)*610;top=220+(panel_index//2)*680
        box=dict(left=xleft,right=xleft+520,top=top,bottom=top+245)
        xd=[clock(case['window_start']),clock(case['window_end'])]
        if not xd[0]<xd[1]:raise ValueError('saved empirical window')
        mi=[i for i,r in enumerate(minute_rows) if r['case_id']==case['id'] and xd[0]<=clock(r['available_at'])<=xd[1]]
        ci=[i for i,r in enumerate(cloud_rows) if r['case_id']==case['id'] and xd[0]<=clock(r['available_at'])<=xd[1]]
        if not mi or not ci:raise ValueError('selected case lacks pinned minute/cloud rows')
        if any(minute_rows[i]['contract']!=case['contract'] or minute_rows[i]['episode_id']!=case['episode_id'] for i in mi) or any(cloud_rows[i]['contract']!=case['contract'] or cloud_rows[i]['episode_id']!=case['episode_id'] for i in ci):raise ValueError('saved empirical contract/episode mismatch')
        values=[scalar(minute_rows[i]['close']) for i in mi]
        values.extend(scalar(cloud_rows[i][key]) for i in ci for key in ('ema20','ema50') if cloud_rows[i]['usable'].lower()=='true' and cloud_rows[i]['feature_valid'].lower()=='true')
        values.extend(case.get(key) for key in ('range_high','midpoint','range_low','frozen_level','parent_initial_stop','parent_reset_stop','parent_entry_price','parent_exit_price','action_price'))
        for leg in case['legs']:values.extend(leg.get(key) for key in ('initial_stop','reset_stop','entry_price','exit_price'))
        known=[v for v in values if v is not None]
        if not known or any(type(v) not in (int,float) or not math.isfinite(v) for v in known):raise ValueError('finite saved empirical prices')
        low,high=min(known),max(known);padding=max((high-low)*.08,.1)
        yd=[low-padding,high+padding]
        x=lambda at:box['left']+(clock(at)-xd[0])*(box['right']-box['left'])/(xd[1]-xd[0])
        y=lambda price:box['bottom']-(price-yd[0])*(box['bottom']-box['top'])/(yd[1]-yd[0])
        series=[];series_points={}
        for key,artifact,rows,indices in (('close',minutes,minute_rows,mi),('ema20',cloud,cloud_rows,ci),('ema50',cloud,cloud_rows,ci)):
            segments=[];current=[]
            for i in indices:
                value=scalar(rows[i][key]);usable=rows[i]['usable'].lower()=='true' and (key=='close' or rows[i]['feature_valid'].lower()=='true')
                if value is None or not usable:
                    if current:segments.append(current);current=[]
                else:
                    if current and clock(rows[i]['available_at'])-clock(rows[current[-1]]['available_at'])>(60 if key=='close' else 300):segments.append(current);current=[]
                    current.append(i)
            if current:segments.append(current)
            s=dict(id=key,source_artifact=artifact,source_sha256=draft.sources[artifact]['sha256'],source_rows=indices,original_source_rows=[draft.sources[artifact]['selected_source_rows'][i] for i in indices],row_selectors={'case_id':case['id']},x_column='available_at',y_column=key,segments=segments,contract_column='contract',episode_column='episode_id',availability_column='available_at')
            if key=='close':s['validity_column']='usable'
            else:s['validity_columns']=['usable','feature_valid']
            series.append(s);series_points[key]=[]
            for segment_index,segment in enumerate(segments):
                xy=[(x(rows[i]['available_at']),y(scalar(rows[i][key]))) for i in segment]
                series_points[key].append(xy)
                dash=' stroke-dasharray="8 4"' if key=='ema50' else ''
                svg.append(f'<polyline data-panel="{escape(panel_id)}" data-series="{key}" data-segment="{segment_index}" points="'+ ' '.join(number(a)+','+number(b) for a,b in xy)+f'" fill="none" stroke="{COLORS[key]}" stroke-width="2"{dash}/>')
        if series[1]['segments']!=series[2]['segments']:raise ValueError('EMA cloud band needs aligned known/null rows')
        bands=[dict(id='ema-cloud',upper_series='ema20',lower_series='ema50')]
        for i,(first,last) in enumerate(zip(series_points['ema20'],series_points['ema50'])):
            xy=first+list(reversed(last))
            svg.append(f'<polygon data-panel="{escape(panel_id)}" data-cloud-band="ema-cloud" data-segment="{i}" points="'+ ' '.join(number(a)+','+number(b) for a,b in xy)+'" fill="#d9c9ee" fill-opacity=".18"/>')
        # Redraw lines over the translucent band without duplicating geometry.
        # Bands remain translucent, so retained SVG series stay one per segment.
        b=lambda key:binding(draft,case_art,pointer+'/'+key)
        case_bindings={key:b(key) for key in ('episode_id','contract','policy','mode','leg')}
        own_timing=[]
        def relation(id,left,right,operator='le'):
            id=case['id']+'-'+id;timing.append(dict(id=id,left=left,operator=operator,right=right));own_timing.append(id)
        relation('full-post-fill-contact',b('parent_fill_upper'),b('contact_open'))
        frozen_start_key='frozen_level_contact_open' if case.get('frozen_level_contact_open') else 'contact_open'
        if frozen_start_key!='contact_open':relation('full-post-fill-first-failure',b('parent_fill_upper'),b(frozen_start_key))
        prior=[i for i in ci if cloud_rows[i]['usable'].lower()=='true' and cloud_rows[i]['feature_valid'].lower()=='true' and clock(cloud_rows[i]['available_at'])<=clock(case[frozen_start_key])]
        if 'frozen_level_available_at' in case and case['frozen_level_available_at'] is not None:relation('frozen-prior-cloud',b('frozen_level_available_at'),b(frozen_start_key))
        elif prior:relation('displayed-prior-cloud',csv_binding(draft,cloud,prior[-1],'available_at'),b('contact_open'))
        if case.get('action_at') is not None:relation('signal-before-action',b('signal_at'),b('action_at'))
        markers=[];levels=[];annotations=[]
        def marker(id,time_key,price_key,color):
            at,price=case.get(time_key),case.get(price_key)
            if at is None or price is None:return
            if not xd[0]<=clock(at)<=xd[1]:raise ValueError('saved marker outside observed window')
            markers.append(dict(id=id,time=at,price=price,time_binding=b(time_key),price_binding=b(price_key)))
            svg.append(f'<circle data-panel="{escape(panel_id)}" data-marker="{id}" cx="{number(x(at))}" cy="{number(y(price))}" r="4.5" fill="{color}" stroke="#ffffff"/>')
            label={'original-fill':'Original fill','actual-policy-action':'Policy action','parent-comparator-exit':'Parent comparator exit'}[id]
            anchor='end' if x(at)>(box['left']+box['right'])/2 else 'start'
            svg.append(svg_text(x(at)-7 if anchor=='end' else x(at)+7,y(price)-8,label,12,color=color,anchor=anchor))
        marker('original-fill','parent_entry','parent_entry_price','#21778f')
        marker('actual-policy-action','action_at','action_price','#9b3e5a')
        marker('parent-comparator-exit','parent_exit','parent_exit_price','#596d65')
        def level(id,price,price_binding,start,start_binding,end,end_binding,color):
            if price is None or start is None or end is None:return
            if not xd[0]<=clock(start)<=clock(end)<=xd[1]:raise ValueError('saved level outside observed window')
            levels.append(dict(id=id,price=price,price_binding=price_binding,start_time=start,start_binding=start_binding,end_time=end,end_binding=end_binding))
            svg.append(f'<line data-panel="{escape(panel_id)}" data-level="{id}" x1="{number(x(start))}" x2="{number(x(end))}" y1="{number(y(price))}" y2="{number(y(price))}" stroke="{color}" stroke-width="1.5" stroke-dasharray="5 4"/>')
            label={'range-H':'H','range-M':'M','range-L':'L','frozen-contact':'Frozen contact/edge','parent-initial-stop':'Parent initial stop','parent-reset-stop':'Parent reset stop','add-initial-stop':'Add initial stop','add-reset-stop':'Add reset stop'}[id]
            display=dict(style='number',precision=1,grouping=True)
            annotations.append(dict(id=id+'-price',source_binding=price_binding,display=display,prefix=label+' '))
            svg.append(f'<text data-panel="{escape(panel_id)}" data-annotation="{id}-price" x="{xleft:g}" y="{number(y(price)-4)}" font-size="12" fill="{color}">{escape(label+" "+token(price,display))}</text>')
        for key,label in (('range_high','H'),('midpoint','M'),('range_low','L')):
            if key in case and case[key] is not None:level('range-'+label,case[key],b(key),case['window_start'],b('window_start'),case['window_end'],b('window_end'),'#bcc4bb')
        level('frozen-contact',case.get('frozen_level'),b('frozen_level'),case[frozen_start_key],b(frozen_start_key),case['signal_at'],b('signal_at'),'#69498f')
        parent_end_key='parent_exit' if case.get('parent_exit') else 'window_end'
        initial_end_key='parent_reset_at' if case.get('parent_reset_stop') is not None and case.get('parent_reset_at') else parent_end_key
        level('parent-initial-stop',case.get('parent_initial_stop'),b('parent_initial_stop'),case['parent_entry'],b('parent_entry'),case[initial_end_key],b(initial_end_key),'#b76735')
        if case.get('parent_reset_stop') is not None and case.get('parent_reset_at'):
            level('parent-reset-stop',case['parent_reset_stop'],b('parent_reset_stop'),case['parent_reset_at'],b('parent_reset_at'),case[parent_end_key],b(parent_end_key),'#b34242')
        ownlegs=[(i,leg) for i,leg in enumerate(case['legs']) if leg.get('leg')=='add']
        for leg_index,leg in ownlegs:
            lb=lambda key:binding(draft,case_art,pointer+'/legs/'+str(leg_index)+'/'+key)
            end_key='exit_time' if leg.get('exit_time') else None
            end=leg['exit_time'] if end_key else case['window_end'];end_binding=lb(end_key) if end_key else b('window_end')
            reset=leg.get('reset_stop_active_at') if leg.get('reset_stop') is not None else None
            level('add-initial-stop',leg.get('initial_stop'),lb('initial_stop'),leg['entry_time'],lb('entry_time'),reset or end,lb('reset_stop_active_at') if reset else end_binding,'#db9343')
            if reset:level('add-reset-stop',leg['reset_stop'],lb('reset_stop'),reset,lb('reset_stop_active_at'),end,end_binding,'#c93452')
        caption_y=box['bottom']+29
        def annotation(id,value,source_binding,prefix='',precision=1):
            nonlocal caption_y
            display={'style':'number','precision':precision,'grouping':True} if type(value) in (int,float) else {'style':'verbatim'}
            text=prefix+token(value,display)
            annotations.append(dict(id=id,source_binding=source_binding,display=display,prefix=prefix))
            svg.append(f'<text data-panel="{escape(panel_id)}" data-annotation="{id}" x="{xleft:g}" y="{caption_y:g}" font-size="15" fill="#24322d">{escape(text)}</text>');caption_y+=21
        # Each annotation is independently bound at its own panel, including nulls.
        annotation('observed-start',case['window_start'],b('window_start'),'Observed path from ')
        annotation('observed-end',case['window_end'],b('window_end'),'Observed path to ')
        annotation('original-fill-clock',case['parent_entry'],b('parent_entry'),'Original modeled fill ')
        annotation('contact-open-clock',case['contact_open'],b('contact_open'),'Contact / confirmation candle opens ')
        if frozen_start_key!='contact_open':annotation('frozen-origin-clock',case[frozen_start_key],b(frozen_start_key),'First failure candle / frozen edge from ')
        annotation('signal-clock',case['signal_at'],b('signal_at'),'Confirmed signal ')
        annotation('action-clock',case.get('action_at'),b('action_at'),'Actual modeled action ')
        annotation('parent-open',case['parent_open_at_signal'],b('parent_open_at_signal'),'Parent OPEN at signal: ')
        annotation('liquidation-net',case.get('liquidation_net'),b('liquidation_net'),'Parent liquidation estimate USD: ',2)
        if policy!='X2':annotation('frozen-price',case.get('frozen_level'),b('frozen_level'),'Frozen contact/edge GC price: ',1)
        if ownlegs:
            i,leg=ownlegs[0];lb=lambda key:binding(draft,case_art,pointer+'/legs/'+str(i)+'/'+key)
            if 'risk_initial_dollars' in leg:annotation('own-leg-risk',leg['risk_initial_dollars'],lb('risk_initial_dollars'),'Add own initial risk USD: ',2)
            if 'quantity' in leg:annotation('own-leg-quantity',leg['quantity'],lb('quantity'),'Add whole-GC quantity: ',0)
            annotation('own-initial-stop',leg.get('initial_stop'),lb('initial_stop'),'Add initial stop GC price: ')
            if 'reset_stop' in leg:annotation('own-reset-stop',leg.get('reset_stop'),lb('reset_stop'),'Add reset stop GC price: ')
        else:annotation('case-kind',case['kind'],b('kind'),'Support outcome / no filled add: ' if policy.startswith('A') else 'Selected exit comparison: ')
        heading=policy+' '+case['kind'].replace('_',' ')+' '+('long' if case['direction']==1 else 'short')
        svg.append(svg_text(xleft,top-40,heading,21));svg.append(svg_text(xleft,top-17,case['mode']+' / '+case['leg']+'; contract '+case['contract'],15))
        svg.append(svg_text(xleft,box['bottom']+330,'GC prices / UTC; EMA20 solid, EMA50 dashed',15))
        panels.append(dict(id=panel_id,episode_id=case['episode_id'],contract=case['contract'],policy=policy,mode=case['mode'],leg=case['leg'],case_bindings=case_bindings,timing_assertion_ids=own_timing,plot_box=box,x_domain=xd,y_domain=yd,series=series,bands=bands,markers=markers,levels=levels,annotations=annotations))
    svg.append('</svg>')
    source=draft.sources[minutes]
    plotted=[dict(source_row=i,original_source_row=source['selected_source_rows'][i],values={'case_id':r['case_id'],'episode_id':r['episode_id'],'contract':r['contract'],'available_at':r['available_at'],'close':scalar(r['close'])}) for i,r in enumerate(minute_rows)]
    provenance=dict(kind='empirical-example',source_artifact=minutes,source_sha256=source['sha256'],plotted_values=plotted,selection_artifact=case_art,selection_sha256=draft.sources[case_art]['sha256'],selection_case_pointers=['/cases/'+str(i) for i,_ in selected],timing_assertions=timing,plot_encoding=dict(kind='cloud-path-v1',coordinate_precision=6,canvas=[width,height],panels=panels))
    return '\n'.join(svg).encode(),provenance


def add_cloud_examples(draft,sections):
    """Append only the saved selected cases for a condition's Summary view."""
    if draft.spec.view!='summary' or draft.spec.group not in POLICIES:return sections
    if 'example-selection.json' not in draft.sources:draft.copy_json('example-selection.json')
    selected=json.loads(draft.files['example-selection.json'])
    if selected['run_id']!=draft.run_id or selected['schema_version']!='study23.phase3-balanced-examples/v1':raise ValueError('selected example source identity')
    for policy in POLICIES[draft.spec.group]:
        absent=[(i,c) for i,c in enumerate(selected.get('absent_cases',[])) if c['policy']==policy]
        if absent:
            keys=['policy','mode','kind','direction','status']
            cols=[dict(key=k,label='Original direction: 1 long / -1 short' if k=='direction' else k.replace('_',' ').capitalize()) for k in keys]
            sections.append(draft.json_table('cloud-cases-'+policy.lower()+'-absent',policy+' — no qualifying saved case in requested category','example-selection.json',[{k:'/absent_cases/'+str(i)+'/'+k for k in keys} for i,_ in absent],cols))
        cases=[(i,c) for i,c in enumerate(selected['cases']) if c['policy']==policy]
        if not cases:continue
        if len(cases)>6 or len({c['id'] for _,c in cases})!=len(cases):raise ValueError('bounded distinct balanced cases')
        svg,provenance=render_policy(draft,policy,cases)
        caption='Earliest chronological saved qualifying cases by frozen kind and side, not best P&L. A20/A50 examples use diagnostic one-plus-one exposure; they are separate from the financed equal-risk comparison. X1/X2 examples use standardized original legs. Curves are unadjusted closes and confirmed five-minute EMA values; modeled action markers include inherited costs. Missing spans and absent actions are not filled in.'
        sections.append(draft.figure('cloud-cases-'+policy.lower(),policy+' — balanced empirical cloud cases','cloud-cases-'+policy.lower(),svg,provenance,alt=policy+' selected long/short saved examples with available cloud clocks, original/action markers and separately saved stop/risk levels.',caption=caption))
    limit=30 if any(s['id']=='uncertainty' for s in sections) else 29
    if len(sections)>limit or len(draft.figures)>12:raise ValueError('cloud example report bound')
    return sections
