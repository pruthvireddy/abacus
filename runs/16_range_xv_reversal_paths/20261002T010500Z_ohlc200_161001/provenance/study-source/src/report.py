"""Offline reports and SVG charts rendered exclusively from saved numerical tables."""
from __future__ import annotations
import html,json
from pathlib import Path
import numpy as np
import pandas as pd
from .common import load,dump,clean,STUDY

def fmt(v):
    if pd.isna(v):return 'undefined'
    if isinstance(v,(int,np.integer)):return str(v)
    if isinstance(v,(float,np.floating)):
        if v==int(v) and abs(v)<1e8:return str(int(v))
        return f'{v:.4g}'
    return str(v)

class Renderer:
    def __init__(self,out):self.out=out;self.tables={p.stem:pd.read_csv(p) for p in (out/'tables').glob('*.csv')};self.md=[];self.body=[]
    def para(self,text):self.md.append(text+'\n');self.body.append('<p>'+html.escape(text)+'</p>')
    def heading(self,title,level=2,id_=None):
        self.md.append('#'*level+' '+title+'\n');self.body.append(f'<h{level}'+(f' id="{id_}"' if id_ else '')+'>'+html.escape(title)+f'</h{level}>')
    def table(self,name,df,columns,title=None):
        if title:self.heading(title,3)
        self.body.append('<div class="scroll"><table><thead><tr>'+''.join('<th>'+html.escape(c)+'</th>' for c in columns)+'</tr></thead><tbody>')
        self.md.append('| '+' | '.join(columns)+' |\n| '+' | '.join(['---']*len(columns))+' |')
        for ix,row in df.iterrows():
            self.body.append('<tr>');cells=[]
            for c in columns:
                v=row[c];s=fmt(v);cells.append(s)
                if isinstance(v,(float,int,np.floating,np.integer)) or pd.isna(v):
                    vv='null' if pd.isna(v) else repr(float(v))
                    attr=f' data-table="{name}" data-row="{ix}" data-column="{c}" data-value="{vv}"'
                else:attr=''
                self.body.append('<td'+attr+'>'+html.escape(s)+'</td>')
            self.body.append('</tr>');self.md.append('| '+' | '.join(cells)+' |')
        self.body.append('</tbody></table></div>');self.md.append('')
    def figure(self,path,caption):
        self.body.append('<figure><img src="'+path+'" alt="'+html.escape(caption,quote=True)+'"><figcaption>'+html.escape(caption)+'</figcaption></figure>')
        self.md.append('!['+caption+']('+path+')\n')

def svg(out,name,title,marks,sources,width=900,height=360):
    p=out/'figures'/name;p.parent.mkdir(exist_ok=True)
    meta=json.dumps(clean({'sources':sources}),allow_nan=False)
    p.write_text(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img">'+
      '<title>'+html.escape(title)+'</title><metadata>'+html.escape(meta)+'</metadata><rect width="100%" height="100%" fill="#f8fafc"/>'+
      '<g font-family="Arial,sans-serif" font-size="14" fill="#172033"><text x="25" y="25" font-size="18">'+html.escape(title)+'</text>'+''.join(marks)+'</g></svg>')
    return 'figures/'+name
def source(name,index,column,value):return {'table':name,'row':int(index),'column':column,'value':None if pd.isna(value) else float(value)}
def lineplot(out,name,title,series,xlabel,ylabel):
    marks=[];sources=[];xmin=min(x for _,data,_ in series for x,_,_ in data);xmax=max(x for _,data,_ in series for x,_,_ in data)
    vals=[v for _,data,_ in series for _,v,_ in data if np.isfinite(v)];ymin=min(0,min(vals)) if vals else 0;ymax=max(vals) if vals else 1
    if ymax<=ymin:ymax=ymin+1
    ymax+=.06*(ymax-ymin);colors=['#2563eb','#dc2626','#059669','#7c3aed']
    def xx(x):return 70+720*(x-xmin)/max(1,xmax-xmin)
    def yy(y):return 285-220*(y-ymin)/(ymax-ymin)
    marks.append('<path d="M70 60V285H790" stroke="#64748b" fill="none"/>')
    for i in range(6):
        y=ymin+(ymax-ymin)*i/5;marks.append(f'<text x="8" y="{yy(y)+5:.3f}">{y:.3g}</text><line x1="70" x2="790" y1="{yy(y):.3f}" y2="{yy(y):.3f}" stroke="#e2e8f0"/>')
    for j,(label,data,_) in enumerate(series):
        points=' '.join(f'{xx(x):.3f},{yy(v):.3f}' for x,v,s in data if np.isfinite(v));color=colors[j%len(colors)]
        marks.append('<polyline points="'+points+'" fill="none" stroke="'+color+'" stroke-width="2"/>')
        for x,v,s in data:
            if not np.isfinite(v):continue
            marks.append(f'<circle cx="{xx(x):.3f}" cy="{yy(v):.3f}" r="4" fill="{color}"><title>{html.escape(label)}: {v:.6g}</title></circle>');sources.append(s)
        marks.append(f'<text x="{80+j*180}" y="320" fill="{color}">{html.escape(label)}</text>')
    for x in sorted(set(x for _,data,_ in series for x,_,_ in data)):
        marks.append(f'<text x="{xx(x)-5:.3f}" y="305">{x:g}</text>')
    marks.append('<text x="370" y="350">'+html.escape(xlabel+' / '+ylabel)+'</text>')
    return svg(out,name,title,marks,sources)

def figures_for(r,chart,d):
    slug=chart+('_bullish' if d==1 else '_bearish');base=r.tables['continuation'];g=base[(base.chart==chart)&(base.direction==d)&base.panel.eq('all')]
    ix=g.index[0];row=g.iloc[0];data=[(k,row[f'common10_p{k}'],source('continuation',ix,f'common10_p{k}',row[f'common10_p{k}'])) for k in range(1,11)]
    r.figure(lineplot(r.out,slug+'-continuation.svg',f'{slug}: common ten-bar continuation, n={int(row.common10_n)}',[('P(F>=k)',data,None)],'additional bars k','probability'), 'Common ten-physical-bar cohort; R excluded from F.')
    matrix=r.tables['L-F-matrix'];mm=matrix[(matrix.chart==chart)&(matrix.direction==d)&matrix.panel.eq('L')];lbins=[str(i) for i in range(1,11)]+['11-15','16+'];fbins=['0','1','2','3','4','5','6-7','8-9','10+','unresolved']
    marks=[];sources=[]
    for ix,row in mm.iterrows():
        if str(row.level) not in lbins:continue
        x=120+fbins.index(str(row.F_bin))*72;y=75+lbins.index(str(row.level))*30;v=row.percentage
        color=f'rgb({int(245-140*(v if np.isfinite(v) else 0))},{int(248-70*(v if np.isfinite(v) else 0))},255)'
        marks.append(f'<rect x="{x}" y="{y}" width="70" height="28" fill="{color}"/><text x="{x+5}" y="{y+19}">{v:.1%}</text>');sources.append(source('L-F-matrix',ix,'percentage',v))
    for j,lb in enumerate(lbins):marks.append(f'<text x="20" y="{94+j*30}">L={lb}</text>')
    for j,fb in enumerate(fbins):marks.append(f'<text x="{120+j*72}" y="60">F {fb}</text>')
    r.figure(svg(r.out,slug+'-L-F.svg',slug+': L-to-F row percentages',marks,sources,height=470),'Exact bins require a completed breaker; unresolved includes censored lower bounds below ten.')
    pp=r.tables['price-paths'];sub=pp[(pp.chart==chart)&(pp.direction==d)&pp.panel.eq('L')&pp.horizon.eq(3)&pp.cohort.eq('strict')]
    data=[(lbins.index(str(row.level))+1,row.D_q_mean,source('price-paths',ix,'D_q_mean',row.D_q_mean)) for ix,row in sub.iterrows()]
    r.figure(lineplot(r.out,slug+'-delta.svg',slug+': three-bar signed landing by prior L',[('mean D3',data,None)],'L bins (11=11–15,12=16+)','constant q equivalents'),'B1-open reference to B4-open mark, strict positive duration; all colours included.')
    dist=r.tables['distributions'];ss=dist[(dist.chart==chart)&(dist.direction==d)]
    for name,cols in [('excursions',['h3_MAE_q','h3_MFE_q']),('elapsed',['h3_elapsed_seconds'])]:
        series=[]
        for col in cols:
            g=ss[ss.metric==col];data=[(int(row['bin']),row.share,source('distributions',ix,'share',row.share)) for ix,row in g.iterrows()];series.append((col,data,None))
        r.figure(lineplot(r.out,slug+'-'+name+'.svg',slug+': '+name+' distribution',series,'saved distribution bin index','share'),'Exact bin edges and counts are in distributions.csv; MAE/MFE exclude R and include the exit gap.')
    cal=r.tables['model-calibration'];ss=cal[(cal.chart==chart)&(cal.direction==d)&cal.target.eq('F3')];series=[]
    for model in ['B0','B1','M1','M2']:
        g=ss[(ss.model==model)&ss.n.gt(0)];data=[(row.mean_prediction,row.mean_observed,source('model-calibration',ix,'mean_observed',row.mean_observed)) for ix,row in g.iterrows()];series.append((model,data,None))
    if any(data for _,data,_ in series):r.figure(lineplot(r.out,slug+'-calibration.svg',slug+': later F3 calibration',series,'predicted probability','observed probability'),'Frozen predictions; fixed probability bins; counts in model-calibration.csv.')
    lift=r.tables['matched-L-lifts'];ss=lift[(lift.chart==chart)&(lift.direction==d)&lift.split.eq('later')&lift.metric.eq('y3')]
    data=[(lbins.index(str(row.L_bin))+1,row.difference,source('matched-L-lifts',ix,'difference',row.difference)) for ix,row in ss.iterrows()]
    r.figure(lineplot(r.out,slug+'-lift.svg',slug+': later L-specific lift',[('raw lift',data,None)],'L bin','absolute probability difference'),'Same chart/direction and order3 eligibility; standardized differences and uncertainty in matched-L-lifts.csv.')

def source_figures(r):
    table=r.tables['source-example-bars']
    for (ch,d,case,event),g in table.groupby(['chart','direction','case','event_id']):
        if case not in ['L2_F0','L3_F4']:continue
        lo=g.low_price.min();hi=g.high_price.max();span=max(hi-lo,1e-9);marks=[];sources=[]
        for j,(ix,row) in enumerate(g.iterrows()):
            x=90+j*55
            def yy(v):return 280-210*(v-lo)/span
            color='#dc2626' if row.close_price<row.open_price else '#059669' if row.close_price>row.open_price else '#64748b'
            marks.append(f'<line x1="{x}" x2="{x}" y1="{yy(row.high_price):.3f}" y2="{yy(row.low_price):.3f}" stroke="{color}"/>'+
              f'<rect x="{x-10}" y="{min(yy(row.open_price),yy(row.close_price)):.3f}" width="20" height="{max(1,abs(yy(row.open_price)-yy(row.close_price))):.3f}" fill="{color}"/>'+
              f'<text x="{x-10}" y="305">'+('R' if row.relative_bar==0 else f'{int(row.relative_bar):+d}')+'</text>')
            for c in ['open_price','high_price','low_price','close_price']:sources.append(source('source-example-bars',ix,c,row[c]))
        r.figure(svg(r.out,ch+f'-{d}-{case}.svg',f'{ch} direction {d}: {case}, source event {event}',marks,sources),'Computed OHLC audit example; labels show physical bar positions around R; no chart screenshot.')

def render(out):
    out=Path(out).resolve()
    if not (out/'tables'/'source-row-audits.csv').exists():
        from .verification import audit_sources
        audit_sources(out,pd.read_parquet(out/'evidence'/'events.parquet'))
    r=Renderer(out);r.heading('Range XV reversals: continuation, landing and predictive lead-up',1,'top')
    r.para('Completed protocol 2.0.0. Eight pinned FX charts are kept separate by bullish/bearish reversal direction. OHLC alone identifies the events. No GUI, screenshots, browser automation or external publication were used.')
    r.para('R is already completed before the reference entry. L excludes R; F counts only consecutive completed followers. A doji breaks a leg. The primary price reference enters at B1 open and marks at B4 open after three physical future bars regardless of colour. These are price-path associations, not verified executable trading profits.')
    cont=r.tables['continuation'];baseline=cont[cont.panel=='all'];paths=r.tables['price-paths'];p3=paths[paths.panel.eq('all')&paths.horizon.eq(3)&paths.cohort.eq('strict')]
    r.heading('Direct answers',2,'answers')
    r.para('1. Baseline follow-through and typical count: the table gives threshold-specific rates and the common three-bar cohort. The capped mean, median and mode use one common ten-bar cohort. Exact F and censor bounds are separate in continuation.csv. High persistence may reflect price-event chart construction.')
    r.table('continuation',baseline,['chart','direction','n','common3_n','common3_p1','common3_p2','common3_p3','p5','p10','common10_n','cap10_mean','cap10_median','cap10_mode','F_exact_mean','unresolved_F'])
    r.para('2. L=2 versus L=3: differences below are L3 minus L2 on identical physical-window rules, with paired session uncertainty and five-session sensitivity. The saved matched-L-lifts table includes every other prior-length bin, raw and window/era-standardized comparisons. L2-L3-adjustment.csv compares later residual differences after frozen R/context and lead-up model expectations.')
    direct=r.tables['L2-L3-direct'];r.table('L2-L3-direct',direct[direct.split.eq('later')],['chart','direction','metric','n2','n3','L3_minus_L2','low','high','standardized_difference','standardized_low','standardized_high','block5_low','block5_high'])
    r.para('3. Incremental later prediction: positive improvements mean lower loss than the reference model. B1 uses context and R geometry; M1 adds L; M2 adds richer history. Interval bounds and the block sensitivity establish support separately for each chart/direction. Model choice was saved after validation, before later metrics were read. Prior input and earlier-study inspection means this is not a pristine holdout or a familywise-confirmatory claim.')
    paired=r.tables['model-paired-improvements'];primary=paired[paired.target.eq('F3')&paired.metric.eq('log_loss')&((paired.model.eq('M1')&paired.baseline.eq('B1'))|(paired.model.eq('M2')&paired.baseline.isin(['M1','B1'])))]
    r.table('model-paired-improvements',primary,['chart','direction','model','baseline','improvement','low','high','block5_low','block5_high','n'])
    r.para('4–6. Three-bar landing, signed delta, excursion tails and elapsed time: strict positive-duration paths are below. Favourable/flat/adverse are signed landing probabilities. MAE/MFE are nonnegative and include entry, B1–B3 extremes and B4 open, including gaps. R range is excluded. Constant q equivalents do not change with historical tick eras; raw prices and separate historical units remain in evidence. Elapsed time is a proxy and varies with price-event bars.')
    r.table('price-paths',p3,['chart','direction','n','dates','favourable','flat','adverse','D_q_mean','D_q_low','D_q_high','D_q_median','D_q_p10','MAE_q_mean','MAE_q_p95','MFE_q_mean','MFE_q_p95','elapsed_seconds_mean','elapsed_seconds_median','elapsed_seconds_p90','within_1_minutes','within_5_minutes','within_15_minutes','within_30_minutes'])
    r.para('F>=3 can still land adversely; early colour breaks can land favourably. The joint table counts both and retains flat landings. Same-second price paths are a descriptive sensitivity with unresolved execution opportunities. Time-to-followers is conditional on attainment and includes all-candidate failure/unresolved counts. The clock-mark table uses stale completed closes with actual timestamps and explicit coverage, never an exact market price at T.')
    r.table('failure-landing-joint',r.tables['failure-landing-joint'],['chart','direction','F_ge3','landing','n','denominator'])
    r.para('7. Conditions: at most one per nominated type was selected using development/validation support only. Every nominated condition appears below, including later failure, coverage and pointwise uncertainty. A later lower lift bound above zero with adequate support is a descriptive supported association; bounds spanning zero are inconclusive; a nonpositive lift contradicts the nominated continuation hypothesis. Price, risk and time can disagree with colour lift.')
    candidates=r.tables['candidate-evaluation']
    if len(candidates):
        ss=candidates[candidates.split.eq('later')&candidates.panel.isna()] if 'panel' in candidates else candidates[candidates.split.eq('later')]
        r.table('candidate-evaluation',ss,['candidate_id','chart','direction','predicates','coverage','order_n','order_dates','p3','baseline_p3','lift','lift_low','lift_high','block5_low','block5_high','D_q_mean','MAE_q_mean','MFE_q_mean','elapsed_seconds_mean','F3_and_adverse_n','early_break_and_favourable_n'])
    else:r.para('No condition met the prespecified development/validation nomination requirements; none was carried into later evaluation.')
    r.heading('Interpretation and limits',2,'limits')
    r.para('Continuation is chart-colour persistence. Model improvements, if supported, measure incremental predictive association within these exports. Correlated settings and instruments are not independent confirmations. No volume/order-flow delta is present. Unknown contract-roll/adjustment history, inferred clocks, completion proxies, intrabar ambiguity and unavailable fills/spreads prevent an executable edge claim.')
    r.para('Fixed assumed round-trip costs of 1/2/4 q are sensitivity calculations on gross D, not observed trading costs. Positive mean D is only a gross cost allowance. Excursion attainment at half/one R span is OHLC reachability; it cannot establish stop-versus-target order. No optimizer or hindsight MFE exit is used. Censor bounds avoid assuming random censoring, and sparse cells are flagged below 100 events or 30 dates.')
    r.para('The 6S pre/post trade-date 2022-05-02 panels are mandatory. Off-grid prices remain unrounded and raw evidence is retained. The primary first/final sessions are excluded. Repeated records create barriers. Long gaps and prior same-second observations are disclosed with sensitivities. Full-history quartiles never enter the predictors; discovery-only bins remain frozen.')
    r.heading('Input and cohort audit',2,'audit')
    r.table('input-quality',r.tables['input-quality'],['chart','rows','session_dates','repeated','doji','same_second','long_gaps_gt_3600','off_grid_constant','off_grid_historical','unavailable'])
    r.table('eligibility',r.tables['eligibility'],['chart','direction','horizon','candidate','order_eligible','strict_eligible','same_second_excluded','boundary_excluded','zero_event_dates'])
    r.heading('Chart and direction evidence',2,'charts')
    for (chart,d),g in baseline.groupby(['chart','direction']):
        r.heading(chart+' '+('bullish' if d==1 else 'bearish'),2,chart+f'-{d}')
        r.table('continuation',cont[(cont.chart==chart)&(cont.direction==d)&cont.panel.eq('L')],['level','n','common3_n','common3_p1','common3_p2','common3_p3','p3_low','p3_high','cap10_mean','cap10_median','unresolved_F'])
        r.table('price-paths',paths[(paths.chart==chart)&(paths.direction==d)&paths.panel.eq('L')&paths.horizon.eq(3)],['level','n','D_q_mean','D_q_median','favourable','MAE_q_mean','MAE_q_p95','MFE_q_mean','elapsed_seconds_mean'])
        figures_for(r,chart,d)
    r.heading('Computed source-row examples',2,'examples');source_figures(r)
    r.heading('Saved numerical evidence and reproduction',2,'evidence')
    r.para('All displayed values and figures are generated from saved CSV evidence. Event features and forward labels are separate columns with undefined flags and available_at. Event ledgers, input-row evidence and predictions are retained outside ordinary Git with schema/row counts/checksums in events.manifest.json after sealing. The staged and retained copies are local; off-device backup was not verified.')
    for name in sorted(r.tables):
        r.body.append('<p><a href="tables/'+name+'.csv">'+name+'.csv</a></p>');r.md.append('- ['+name+'.csv](tables/'+name+'.csv)')
    for name in ['config.json','inputs.lock.json','feature-dictionary.json','freeze.json','selection.lock.json','development-quartiles.json','candidate-selection-history.json','final-model-settings.json','metrics.json','executable-protocol.md','plan.md','commands.json']:
        r.body.append('<p><a href="'+name+'">'+name+'</a></p>');r.md.append('- ['+name+']('+name+')')
    r.para('Reproduce from the workspace with the locked environment: UV_CACHE_DIR=.uv-cache OPENBLAS_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 OMP_NUM_THREADS=1 ./scripts/uv run --locked python studies/16_range_xv_reversal_paths/run.py STAGE --out work/16_range_xv_reversal_paths/NEW_UNIQUE_RUN. Stages are prepare, freeze, execute, summarize, verify, seal. Prepare creates a new directory, freeze runs synthetic checks, execute creates labels then locks selection before later evaluation. Reports render saved tables only. Never rerun into a completed run.')
    css='body{font:16px/1.5 system-ui,sans-serif;max-width:1500px;margin:auto;padding:32px;background:#fff;color:#172033}h1,h2{line-height:1.2}h2{margin-top:48px;border-top:1px solid #cbd5e1;padding-top:24px}.scroll{overflow:auto}table{border-collapse:collapse;font-size:13px;width:100%}td,th{border:1px solid #cbd5e1;padding:6px;text-align:right}th{background:#e2e8f0}td:first-child,th:first-child{text-align:left}figure{display:inline-block;width:min(100%,900px);margin:20px 0}img{width:100%}figcaption{font-size:13px;color:#475569}a{color:#1d4ed8}'
    document='<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Range XV reversal paths</title><style>'+css+'</style></head><body><nav><a href="#answers">Answers</a> · <a href="#charts">Charts</a> · <a href="#audit">Audit</a> · <a href="#evidence">Evidence</a></nav>'+''.join(r.body)+'</body></html>'
    (out/'report.html').write_text(document);(out/'report.md').write_text('\n'.join(r.md))
    (out/'advice.md').write_text('# Dated interpretation — October 1, 2026\n\n'+
      'This run supplies descriptive colour continuation, gross price paths and chronological incremental prediction, with negative and inconclusive comparisons retained. Read report.md and the named tables by chart/direction; no pooled independent-confirmation claim is made.\n\n'+
      'L=2/3 comparisons: tables/L2-L3-direct.csv and L2-L3-adjustment.csv. Richer history: tables/model-paired-improvements.csv, primary F3 log loss; inspect calibration, Brier, regression errors and five-session intervals alongside lift. All nominated conditions: tables/candidate-evaluation.csv and candidate-selection-history.json.\n\n'+
      'No executable strategy is selected. Intrabar sequencing, fill timing, bid/ask and contract-roll provenance need independent evidence before an executable profitability study. Retain the negative and sparse results as research evidence.\n')
    print('Offline HTML/Markdown and computed SVG charts rendered from saved evidence.',flush=True)
