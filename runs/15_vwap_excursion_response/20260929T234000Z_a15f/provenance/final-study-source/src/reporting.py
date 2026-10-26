"""Offline reports and SVG figures rendered only from saved evidence tables."""
from __future__ import annotations
import html
import json
import math
import re
from pathlib import Path
import numpy as np
import pandas as pd
from .common import PRODUCTS, SESSIONS, save_table, dump, sha, utcnow

LABELS={'asia':'Asia','london':'London','ny':'New York','globex':'Globex'}
COLORS=['#116b78','#c45428','#7653a4','#327947','#b23b58','#877322']
STYLE='''body{font:16px/1.55 system-ui,sans-serif;color:#183340;background:#f7f8f6;margin:0}main{max-width:1220px;margin:auto;padding:36px 28px 70px}h1{font-size:36px;line-height:1.15}h2{border-top:2px solid #c7d5d5;padding-top:24px;margin-top:44px}h3{font-size:25px;color:#116b78}h4{font-size:19px}a{color:#006c8c}nav{display:flex;flex-wrap:wrap;gap:18px;background:#e3ecea;padding:16px;border-radius:8px}.note{background:#e7eeec;padding:18px;border-left:4px solid #116b78}.scroll{overflow:auto;margin:18px 0;border:1px solid #ccd8d7;border-radius:5px}table{border-collapse:collapse;font-size:13px;width:100%;font-variant-numeric:tabular-nums}th,td{padding:10px 12px;border-bottom:1px solid #d7dfdc;text-align:right;vertical-align:top;white-space:nowrap}th{background:#dfeae7;text-align:right;position:sticky;top:0}tr:nth-child(even){background:#eef2ef}td:first-child,th:first-child{text-align:left}img{max-width:100%;height:auto;border:1px solid #d3deda;background:white}details{background:white;padding:14px 20px;margin:18px 0;border:1px solid #d3deda}summary{cursor:pointer;font-weight:650}small{color:#4f666e}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(310px,1fr));gap:16px}code{font-size:13px}p{max-width:1050px}footer{margin-top:48px;color:#526a73}@media(max-width:650px){main{padding:20px 12px}h1{font-size:28px}}'''

def local_time(x):return str(pd.Timestamp(x).tz_convert('America/New_York'))

def number(x,digits=2):return '—' if x is None or pd.isna(x) else f'{float(x):,.{digits}f}'
def integer(x):return '—' if x is None or pd.isna(x) else f'{int(x):,}'
def pct(x):return '—' if x is None or pd.isna(x) else f'{100*float(x):.1f}%'
def estimate(row,key,percent=False):
    fmt=pct if percent else number
    v=row.get(key+'_mean');lo=row.get(key+'_ci_low');hi=row.get(key+'_ci_high')
    text=f'{fmt(v)} [{fmt(lo)}, {fmt(hi)}]'
    if row.get(key+'_boundary_uncertainty_unresolved',False)==True:text+=' †'
    return text

def table(columns,rows):
    escaped=lambda x:html.escape(str(x))
    heads=''.join(f'<th>{escaped(c)}</th>' for c in columns)
    body=''.join('<tr>'+''.join(f'<td>{escaped(v)}</td>' for v in row)+'</tr>' for row in rows)
    md='| '+' | '.join(columns)+' |\n| '+' | '.join(['---']*len(columns))+' |\n'
    md+=''.join('| '+' | '.join(str(v).replace('|','/') for v in row)+' |\n' for row in rows)
    return '<div class="scroll"><table><thead><tr>'+heads+'</tr></thead><tbody>'+body+'</tbody></table></div>',md

class Document:
    def __init__(self,title):self.html=[f'<h1>{html.escape(title)}</h1>'];self.md=['# '+title+'\n']
    def para(self,text,note=False):self.html.append(f'<p class="{"note" if note else ""}">{html.escape(text)}</p>');self.md.append(text+'\n')
    def heading(self,text,level=2):self.html.append(f'<h{level}>{html.escape(text)}</h{level}>');self.md.append('#'*level+' '+text+'\n')
    def tbl(self,columns,rows):a,b=table(columns,rows);self.html.append(a);self.md.append(b)
    def image(self,path,alt):self.html.append(f'<img loading="lazy" src="{path}" alt="{html.escape(alt)}">');self.md.append(f'![{alt}]({path})\n')
    def link(self,path,label):self.html.append(f'<p><a href="{path}">{html.escape(label)}</a></p>');self.md.append(f'[{label}]({path})\n')
    def details(self,title):self.html.append('<details><summary>'+html.escape(title)+'</summary>');self.md.append('### '+title+'\n')
    def end_details(self):self.html.append('</details>')
    def write(self,out,name):
        nav='<nav><a href="report.html">Master</a>'+''.join(f'<a href="{s}.html">{LABELS[s]}</a>' for s in SESSIONS)+'</nav>'
        text='<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+html.escape(self.md[0][2:].strip())+'</title><style>'+STYLE+'</style></head><body><main>'+nav+'\n'.join(self.html)+'<footer>Study 15 · Protocol 1.0.0 · Local research evidence · No external assets</footer></main></body></html>'
        (out/f'{name}.html').write_text(text);(out/f'{name}.md').write_text('\n'.join(self.md))


def svg_plot(path,title,series,xlabel,ylabel,*,vlines=(),bands=False):
    """Simple standalone scientific SVG plot; numeric inputs are saved tables."""
    width,height=920,480;left,top,right,bottom=85,70,25,105
    points=[(float(x),float(y)) for _,xs,ys in series for x,y in zip(xs,ys) if np.isfinite(x) and np.isfinite(y)]
    if not points:return
    xs,ys=zip(*points);axis_x=list(xs)+[v[0] for v in vlines];xmin,xmax=min(axis_x),max(axis_x);ymin,ymax=min(ys),max(ys)
    if xmin==xmax:xmin-=.5;xmax+=.5
    if ymin==ymax:ymin-=1;ymax+=1
    pad=(ymax-ymin)*.08;ymin-=pad;ymax+=pad
    xmap=lambda x:left+(x-xmin)/(xmax-xmin)*(width-left-right)
    ymap=lambda y:height-bottom-(y-ymin)/(ymax-ymin)*(height-top-bottom)
    esc=html.escape
    parts=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img"><title>{esc(title)}</title><rect width="100%" height="100%" fill="#fff"/><g font-family="Arial,sans-serif" font-size="13" fill="#183340">',f'<text x="{left}" y="30" font-size="20">{esc(title)}</text>']
    for k in range(6):
        y=ymin+(ymax-ymin)*k/5;yy=ymap(y)
        parts.append(f'<line x1="{left}" x2="{width-right}" y1="{yy:.2f}" y2="{yy:.2f}" stroke="#e1e7e5"/><text x="{left-10}" y="{yy+4:.2f}" text-anchor="end">{y:.2f}</text>')
    xticks=sorted(set(xs)) if len(set(xs))<=12 else np.linspace(xmin,xmax,6)
    for x in xticks:
        xx=xmap(x)
        parts.append(f'<text x="{xx:.2f}" y="{height-bottom+25}" text-anchor="middle">{x:.0f}</text>')
    for j,(label,x,y) in enumerate(series):
        coords=' '.join(f'{xmap(float(a)):.2f},{ymap(float(b)):.2f}' for a,b in zip(x,y) if np.isfinite(a) and np.isfinite(b))
        parts.append(f'<polyline points="{coords}" fill="none" stroke="{COLORS[j%len(COLORS)]}" stroke-width="2"/>')
        parts.append(f'<text x="{left+(j%3)*270}" y="{height-35+(j//3)*18}" fill="{COLORS[j%len(COLORS)]}">{esc(label)}</text>')
    for j,(x,label) in enumerate(vlines):
        if xmin<=x<=xmax:
            label_x=min(xmap(x)+4,width-right-130)
            parts.append(f'<line x1="{xmap(x):.2f}" x2="{xmap(x):.2f}" y1="{top}" y2="{height-bottom}" stroke="#555" stroke-dasharray="4 4"/><text x="{label_x:.2f}" y="{top+14+18*j}">{esc(label)}</text>')
    parts.append(f'<text x="{(width+left-right)/2}" y="{height-bottom+48}" text-anchor="middle">{esc(xlabel)}</text><text transform="translate(18,{(height+top-bottom)/2}) rotate(-90)" text-anchor="middle">{esc(ylabel)}</text></g></svg>')
    Path(path).write_text(''.join(parts))


def figures(out,summary):
    dest=out/'figures';dest.mkdir(exist_ok=True);inventory=[]
    for session in SESSIONS:
        for product in PRODUCTS:
            base=summary[(summary.session==session)&(summary['product']==product)&(summary.threshold==2)&(summary.side=='both')]
            dep=base[(base.kind=='departure')&(base.scope=='common_50')].sort_values('horizon_bars')
            touch=base[(base.kind=='touch')&(base.scope=='common_50')].sort_values('horizon_bars')
            specs=[('return','Common-50 cumulative VWAP contact',[(ref,dep.horizon_bars,dep[ref+'_touch_mean']*100) for ref in ['evolving','frozen']],'Two-minute candles','Contact %'),
              ('excursion','Departure excursions, common-50',[(c.replace('_',' '),dep.horizon_bars,dep[c+'_mean']) for c in ['primary_mae','primary_mfe']],'Two-minute candles','Price points'),
              ('endpoint','Mean endpoint displacement, common-50',[('departure continuation',dep.horizon_bars,dep.directional_delta_mean),('touch bounce',touch.horizon_bars,touch.directional_delta_mean)],'Two-minute candles','Directional points')]
            # Quantile curves show the distribution instead of hiding tails in means.
            ten=base[(base.kind=='departure')&(base.scope=='all')&(base.horizon_bars==10)]
            if len(ten):
                row=ten.iloc[0]
                specs += [('mae-mfe-distribution','10-candle departure excursion quantiles',[(c.replace('_',' '),[25,50,75,90,95],[row[f'{c}_p{q:02d}'] for q in [25,50,75,90,95]]) for c in ['primary_mae','primary_mfe']],'Percentile','Price points'),
                 ('terminal-distribution','10-candle directional-close quantiles',[('continuation delta',[5,25,50,75,95],[row[f'directional_delta_p{q:02d}'] for q in [5,25,50,75,95]])],'Percentile','Directional points')]
            years=base[(base.kind=='departure')&base.scope.str.match(r'^year_\d{4}$')&(base.horizon_bars==10)].copy()
            years['plot_year']=years.scope.str[-4:].astype(int);years=years.sort_values('plot_year')
            specs += [('year-stability','10-candle evolving-return year stability',[('touch %',years.plot_year,years.evolving_touch_mean*100)],'Session year (2026 YTD)','Contact %')]
            for stem,title,series,xlab,ylab in specs:
                name=f'{session}-{product}-{stem}.svg';svg_plot(dest/name,f'{LABELS[session]} · {product} · {title}',series,xlab,ylab)
                if (dest/name).exists():inventory.append({'file':'figures/'+name,'session':session,'product':product,'kind':stem,'source':'tables/summary.parquet'})
    examples=pd.read_parquet(out/'tables/example-selection.parquet');paths=pd.read_parquet(out/'tables/example-paths.parquet')
    for row in examples.dropna(subset=['horizon_id']).itertuples():
        g=paths[paths.horizon_id==row.horizon_id].sort_values('ts_event');tick=row.min_tick
        x=(pd.to_datetime(g.ts_event)-pd.Timestamp(row.entry_time)).dt.total_seconds()/60
        name=f'example-{row.session}-{row.product}-{row.example_class}.svg'
        series=[('raw high',x,g.high_ticks*tick),('raw low',x,g.low_ticks*tick),
          ('evolving VWAP',x,g.evolving_center_ticks*tick),('touched VWAP' if row.kind=='touch' else 'signal VWAP',x,np.full(len(x),row.touched_vwap) if row.kind=='touch' else g.frozen_center_ticks*tick),('known upper 2σ',x,g.known_upper_2sigma),('known lower 2σ',x,g.known_lower_2sigma)]
        svg_plot(dest/name,f'{row.product} {LABELS[row.session]} · {row.example_class} · {row.session_date}',series,
          'Minutes after measured entry (minute open timestamps)','Raw price points',vlines=[(0,'entry'),(2*row.horizon_bars,'deadline'),(-2,'signal/touch candle')])
        inventory.append({'file':'figures/'+name,'session':row.session,'product':row.product,'kind':'example_'+row.example_class,'source':'tables/example-paths.parquet'})
    save_table(out/'tables/figure-inventory',inventory)
    return examples


METHODS=('The pinned VWAP uses completed two-minute HLC3 weighted by bar volume and a volume-weighted population sigma; it is not trade-by-trade VWAP. Signals are first fresh strict closes beyond 2, 2.5 or 3 sigma within a causal parent excursion. '
 'Entry is the next two-minute open. Horizons 5/10/15/20/50 candles are 10/20/30/40/100 minutes; 15 is supplementary. '
 'Touch is source one-minute range overlap with the tick-rounded ±1-tick VWAP zone available at that minute open. '
 'Evolving VWAP is primary; signal-frozen VWAP is secondary. A gap or reference overtake alone is not a touch. '
 'Touch response begins after the containing two-minute candle closes. All MAE/MFE excludes the signal/touch candle and follows the full horizon. '
 'Upper departures: continuation is long and fade is short; upper-arrival bounce is long and through is short. '
 'Lower departures: continuation is short and fade is long; lower-arrival bounce is short and through is long.')
LIMITS=('The release contains 1,037 ES days, 1,177 NQ days and 825 GC days, selected retrospectively for whole-day completeness. '
 'ES/NQ feature history begins in 2021; GC eligible history begins in 2016; all end September 18, 2026. '
 'Absent minutes can be no-trade intervals; absence is not asserted to be corruption. '
 'This is previously inspected exploratory history, with overlapping sessions and nested thresholds. '
 'No threshold or horizon was optimized. Tick-rounded OHLC contact does not establish an executable fill, and OHLC cannot order two barriers reached in the same minute. '
 'No fees, slippage, position sizing, stops or profitability were tested. Delta means price change; true aggressor volume delta is unavailable.')


def preamble(doc,session=None):
    doc.para('Fresh historical execution · Protocol 1.0.0 · Frozen before new outcomes · 2026 YTD through September 18',True)
    if session:
        a,b,_=SESSIONS[session];doc.para(f'{LABELS[session]} uses its own {a} New York-clock anchor and [{a}, {b}) observation window. Both entry and complete horizons stay inside this window; a final candle closing exactly at the end is eligible. DST uses America/New_York. Globex is a separate overlapping population, not a sum of local sessions.')
    doc.para(METHODS);doc.para(LIMITS)
    doc.para('Intervals are marginal 95% percentile intervals from 2,000 shared ISO-week cluster draws (seed 1501), preserving cross-product/session dependence. Brackets contain intervals. † marks zero/all-success boundary uncertainty unresolved by a degenerate bootstrap. Sparse flags: fewer than 100 events, 30 product-session dates or 20 weeks. Latency summaries condition on actual touching. Unavailable horizons never enter success/failure denominators.')
    doc.link('tables/summary.csv','Full numerical tables: points, ticks, sigma units, tails, contexts, uncertainty and counts')
    doc.link('tables/coverage.csv','Per-horizon eligibility, exclusion reasons, parent/date/week support')


def headline_rows(summary,session=None):
    q=summary[(summary.scope=='all')&(summary.side=='both')&(summary.threshold==2)&summary.horizon_bars.isin([10,50])]
    if session:q=q[q.session==session]
    rows=[]
    for _,d in q[q.kind=='departure'].sort_values(['session','product','horizon_bars']).iterrows():
        t=q[(q.kind=='touch')&(q.session==d.session)&(q['product']==d['product'])&(q.horizon_bars==d.horizon_bars)].iloc[0]
        rows.append([LABELS[d.session],d['product'],int(d.horizon_bars),integer(d.n),estimate(d,'evolving_touch',True),estimate(d,'directional_delta'),integer(t.n),estimate(t,'directional_positive',True)])
    return rows


def response_table(doc,g,touch=False):
    rows=[]
    for _,r in g.sort_values(['threshold','horizon_bars']).iterrows():
        primary='bounce' if touch else 'continuation'
        # Both opposite excursions swap exactly on the same path.
        mae=f'{estimate(r,"primary_mae")} / {number(r.get("primary_mae_p50"))}'
        mfe=f'{estimate(r,"primary_mfe")} / {number(r.get("primary_mfe_p50"))}'
        omae=f'{estimate(r,"opposite_mae")} / {number(r.get("opposite_mae_p50"))}'
        omfe=f'{estimate(r,"opposite_mfe")} / {number(r.get("opposite_mfe_p50"))}'
        row=[number(r.threshold,1),int(r.horizon_bars),integer(r.n),mae,mfe,omae,omfe,
          estimate(r,'directional_delta'),estimate(r,'opposite_directional_delta'),estimate(r,'directional_positive',True),
          estimate(r,'above_entry',True),estimate(r,'final_candle_up',True),integer(r.get('entry_tie_count')),
          f'{integer(r.days)} / {integer(r.weeks)}',integer(r.unavailable),r.support_flag if pd.notna(r.support_flag) and r.support_flag else 'adequate descriptive support']
        if touch:
            row += [' / '.join(integer(r.get('first_'+c+'_count')) for c in ['bounce','through','neither','ambiguous']),integer(r.get('barrier_unavailable'))]
        rows.append(row)
    primary='Bounce' if touch else 'Continuation';opposite='Through' if touch else 'Fade'
    columns=['σ','h','n',primary+' MAE mean [CI] / median',primary+' MFE mean [CI] / median',opposite+' MAE mean [CI] / median',opposite+' MFE mean [CI] / median',primary+' Δ mean [CI]',opposite+' Δ mean [CI]',primary+' endpoint %','Close > entry %','Final candle up %','Entry ties','Days / weeks','Unavailable','Support']
    if touch:columns+=['First B / T / neither / ambiguous','Barrier unavailable']
    doc.tbl(columns,rows)


def return_table(doc,g):
    rows=[]
    for _,r in g.sort_values(['threshold','horizon_bars']).iterrows():
        for ref in ['evolving','frozen']:
            rows.append([number(r.threshold,1),int(r.horizon_bars),ref,integer(r.n),integer(r.get(ref+'_touch_count')),
              estimate(r,ref+'_touch',True),integer(r.get(ref+'_no_touch')),
              f'{number(r.get(ref+"_latency_bars_p50"),1)} / {number(r.get(ref+"_latency_bars_p75"),1)}',
              integer(r.get('any_gap_count')),integer(r.get('any_reference_overtake_count')),integer(r.unavailable),
              integer(r.get('evolving_only_count')),integer(r.get('frozen_only_count'))])
    doc.tbl(['σ','h','Target','n','Touches','Touch % [CI]','No touch','Latency h median / p75','Gap paths','Overtake paths','Unavailable','Evolving only','Frozen only'],rows)


def render(out):
    out=Path(out);summary=pd.read_parquet(out/'tables/summary.parquet').replace({np.nan:None})
    # Keep numeric NaNs in working numeric frame, and sanitize only display helpers.
    summary=pd.read_parquet(out/'tables/summary.parquet');examples=figures(out,summary)
    release=pd.read_parquet(out/'tables/release-coverage.parquet');pilot=pd.read_parquet(out/'pilot/tables/feature-pilot.parquet')
    findings=[]
    for session in SESSIONS:
        doc=Document(LABELS[session]+' — anchored VWAP excursion and return')
        preamble(doc,session)
        doc.heading('Primary 2-sigma overview')
        doc.para('Mirrored upper/lower sides are combined only within each product and session in this overview. The side-specific tables below retain every threshold and horizon. Endpoint bounce frequency describes the closing direction; it differs from the 0.5-sigma first-move race.')
        doc.tbl(['Session','Product','h','Departure n','Evolving return % [CI]','Continuation Δ points [CI]','Touch n','Bounce endpoint % [CI]'],headline_rows(summary,session))
        for product in PRODUCTS:
            doc.heading(product)
            p=pilot[(pilot['product']==product)&(pilot.session==session)]
            doc.para(f'Coverage: {p.session_date.nunique():,} retrospectively eligible dates, {p.session_date.min()} through {p.session_date.max()}. All prices below are raw contract points. Full point/tick/sigma distributions and every tie numerator are saved in summary.csv.')
            cov=release[release['product']==product]
            doc.details(product+' year coverage and retrospective exclusions')
            doc.tbl(['Year','Candidate days','Eligible','Excluded'],[[int(r.year),integer(r.candidate_days),integer(r.eligible_days),integer(r.excluded_days)] for r in cov.itertuples()]);doc.link('tables/release-coverage.csv','Release exclusion reasons by product/year (reasons may overlap)');doc.end_details()
            main=summary[(summary.session==session)&(summary['product']==product)&(summary.scope=='all')]
            for side in ['upper','lower']:
                primary='long' if side=='upper' else 'short';opp='short' if side=='upper' else 'long'
                doc.heading(side.title()+f' departure / arrival: continuation and bounce {primary}; fade and through {opp}',3)
                doc.heading('Departure response',4);response_table(doc,main[(main.kind=='departure')&(main.side==side)])
                doc.heading('VWAP return probability and timing',4);return_table(doc,main[(main.kind=='departure')&(main.side==side)])
                doc.heading('First-return response',4)
                doc.para('Reached-threshold cohorts are nested using crossings recorded before this first touch. Response starts at the next open after touch confirmation. Barrier first move freezes 0.5 touch-close sigma, rounded upward to at least one tick. Counts B/T/neither/ambiguous reconcile separately from unavailable barriers. Same-minute ambiguous is not assigned to either direction. Full-horizon excursions continue after a barrier resolves.')
                response_table(doc,main[(main.kind=='touch')&(main.side==side)],True)
            doc.heading('Common cohort, distribution and year diagnostics',3)
            doc.para('The horizon curves use the identical complete-50 cohort. Distribution quantiles and year diagnostics use each horizon’s eligible cohort. Year 2026 is partial. These diagnostics are descriptive on previously inspected history.')
            for stem in ['return','excursion','endpoint','mae-mfe-distribution','terminal-distribution','year-stability']:
                doc.image(f'figures/{session}-{product}-{stem}.svg',f'{product} {LABELS[session]} {stem}')
            diag=summary[(summary.session==session)&(summary['product']==product)&(summary.side=='both')&(summary.threshold==2)&(summary.horizon_bars==10)&summary.scope.isin(['all','common_50','age_ge30','through_2023','year_2024_period','years_2025_2026'])]
            doc.details('Sensitivity and chronological periods at 10 candles')
            doc.tbl(['Module','Scope','n','Days / weeks','Directional Δ [CI]','Return or bounce endpoint % [CI]'],[[r.kind,r.scope,integer(r.n),f'{integer(r.days)} / {integer(r.weeks)}',estimate(r,'directional_delta'),estimate(r,'evolving_touch' if r.kind=='departure' else 'directional_positive',True)] for _,r in diag.iterrows()]);doc.end_details()
            ex=examples[(examples['product']==product)&(examples.session==session)]
            doc.details('Deterministic source-path examples')
            doc.para('Examples are the earliest stable ID in each prespecified class. They illustrate mechanisms and exclusions, not representative trade quality. The source table includes reference available_at and known sigma for every minute; charts plot raw one-minute high/low and references. Source minute open time relative to entry is shown; contacts have interval resolution. Lines join minute OHLC observations for display and do not imply intraminute order or trades through gaps. The 2-sigma envelope is plotted; 2.5/3-sigma references are retained in the example-path table.')
            for _,r in ex.iterrows():
                if pd.isna(r.horizon_id):doc.para(f'{r.example_class}: no qualifying example.');continue
                doc.para(f'{r.example_class}: {r.horizon_id}; {r.side} side. Signal/confirmation {local_time(r.signal_close_time)}; entry {local_time(r.entry_time)}; deadline {local_time(r.deadline)} (New York time). Frozen sigma {number(r.sigma_signal)} points; signal VWAP {number(r.vwap_signal)}. Band thresholds = VWAP ± 2/2.5/3 × sigma. Exclusion: {r.exclusion_reason if pd.notna(r.exclusion_reason) else "none"}.')
                doc.image(f'figures/example-{session}-{product}-{r.example_class}.svg',str(r.horizon_id))
            doc.end_details()
            r=main[(main.kind=='departure')&(main.side=='both')&(main.threshold==2)&(main.horizon_bars==10)].iloc[0]
            t=main[(main.kind=='touch')&(main.side=='both')&(main.threshold==2)&(main.horizon_bars==10)].iloc[0]
            findings.append({'session':session,'product':product,'horizon':10,'departure_n':int(r.n),
                'return_probability':r.evolving_touch_mean,'return_ci_low':r.evolving_touch_ci_low,'return_ci_high':r.evolving_touch_ci_high,
                'continuation_delta':r.directional_delta_mean,'continuation_ci_low':r.directional_delta_ci_low,'continuation_ci_high':r.directional_delta_ci_high,
                'touch_n':int(t.n),'bounce_endpoint_probability':t.directional_positive_mean,
                'bounce_endpoint_ci_low':t.directional_positive_ci_low,'bounce_endpoint_ci_high':t.directional_positive_ci_high,
                'metric_id_departure':r.metric_id,'metric_id_touch':t.metric_id})
        doc.heading('Interpretation and verification')
        doc.para('Return rates, first-move rates and terminal directional frequencies answer different questions. MAE/MFE maxima are favorable/adverse opportunities on an observed path, not obtainable trading profits. Threshold comparisons are descriptive because signal times and eligible populations differ. Treat sparse cells and boundary uncertainty as unresolved. Shared week intervals do not remove retrospective selection or establish a causal predictor.')
        for file,label in [('verification.json','Numerical verification record'),('advice.md','Dated findings and advice'),('tables/example-selection.csv','Example selection ledger'),('tables/independent-recounts.csv','Independent source recounts'),('events.manifest.json','Retained event evidence and checksums')]:doc.link(file,label)
        doc.write(out,session)
    save_table(out/'tables/findings',findings)
    master=Document('Anchored VWAP — departure, return and first-touch response')
    preamble(master)
    master.heading('The four session populations')
    master.tbl(['Session','New York anchor','Observation window','Report'],[[LABELS[s],a,f'{a}–{b}',s+'.html'] for s,(a,b,_) in SESSIONS.items()])
    for s in SESSIONS:master.link(s+'.html',LABELS[s]+' report: ES, NQ and GC separately')
    master.heading('Primary findings across products and sessions')
    master.para('The table prespecifies 2 sigma at 10 and 50 candles; 10 candles is 20 minutes and 50 is 100 minutes. These rows combine mirrored sides, while the session reports retain upper/lower sides and all 2/2.5/3-sigma thresholds at every requested horizon.')
    master.tbl(['Session','Product','h','Departure n','Evolving return % [CI]','Continuation Δ points [CI]','Touch n','Bounce endpoint % [CI]'],headline_rows(summary))
    master.heading('How to use the evidence')
    master.para('Use the per-horizon denominator for its direct question and common-50 tables when comparing horizon curves. The evolving-minus-frozen paired probability contrast quantifies reference dependence, not price-only mean reversion. Touch-confirmation displacement and next-open location are retained in the event ledger; same-candle movement cannot be credited to the later response entry.')
    master.para('The session reports include all main comparisons, year coverage, common-cohort plots, excursion and terminal-delta distributions, stability diagnostics, warm-up sensitivity and deterministic examples. Full tables also contain marginal anchor-age, local-hour and return-latency cuts. Latency beyond 50 candles belongs to touch-response context, not a new fixed-horizon return estimate.')
    for file,label in [('advice.md','Dated findings and advice'),('metrics.json','Metric definitions and uncertainty'),('verification.json','Numerical verification results'),('input-checks.json','All input hashes and verification'),('events.manifest.json','Event ledger retention and locators'),('protocol-1.0.0.md','Frozen executable protocol'),('tables/release-coverage.csv','Product/year release coverage'),('tables/figure-inventory.csv','Figure inventory and saved-table sources')]:master.link(file,label)
    master.write(out,'report')
    # Advice is generated from the saved findings table, not manually rekeyed numbers.
    saved=pd.read_parquet(out/'tables/findings.parquet')
    lines=['# Dated interpretation — 2026-09-29','', 'This run provides descriptive historical price-path evidence. It does not establish an executable trading edge. The fixed primary comparison below is 2 sigma, mirrored sides, 10 two-minute candles (20 minutes).','']
    for r in saved.itertuples():
        directional='interval includes zero; direction is inconclusive' if r.continuation_ci_low<=0<=r.continuation_ci_high else 'interval excludes zero in this historical sample; costs and executable profitability remain untested'
        lines.append(f'- **{LABELS[r.session]} / {r.product}:** evolving return {pct(r.return_probability)} [{pct(r.return_ci_low)}, {pct(r.return_ci_high)}], n={r.departure_n:,}; continuation delta {number(r.continuation_delta)} points [{number(r.continuation_ci_low)}, {number(r.continuation_ci_high)}] ({directional}). Post-touch bounce endpoint {pct(r.bounce_endpoint_probability)} [{pct(r.bounce_endpoint_ci_low)}, {pct(r.bounce_endpoint_ci_high)}], n={r.touch_n:,}. Evidence: `tables/summary.csv`, `{r.metric_id_departure}` and `{r.metric_id_touch}`.')
    lines += ['',LIMITS,'','Preserve negative and inconclusive cells. A higher-threshold return rate is not a paired improvement over an earlier 2-sigma entry. Long MFE equals short MAE on the same path, so excursion asymmetry alone is not a profit measure. A barrier race is only the specified 0.5-sigma first move.','',
       'No strategy is promoted or existing strategy card overwritten. A future trading study would need separately prespecified execution, costs, controls and genuinely new evaluation history. True volume delta requires a separate pinned source.','',
       '[Master report](report.html) · [Verification](verification.json) · [Full numerical evidence](tables/summary.csv)']
    (out/'advice.md').write_text('\n'.join(lines)+'\n')
    dump(out/'render-record.json',{'rendered_at':utcnow(),'renderer':'study-local offline HTML/Markdown/SVG','numerical_source_sha256':sha(out/'tables/summary.parquet'),
       'reports':[s+ext for s in ['report',*SESSIONS] for ext in ['.html','.md']],
       'figures_source':'tables/summary.parquet and tables/example-paths.parquet','external_assets':False})
