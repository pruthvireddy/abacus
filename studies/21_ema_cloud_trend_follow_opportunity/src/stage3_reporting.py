"""Complete private Stage 3 presentation from explicit saved evidence only."""
from __future__ import annotations

import csv
from datetime import datetime
import html
import importlib
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd

from .reporting import sha256, save_json, read_csv, _html_table, _figure_environment

STUDY_ID="21_ema_cloud_trend_follow_opportunity"
CELLS=tuple((p,i,b) for p in ("ES","GC","NQ") for i in (3,5) for b in ("fast","slow"))
TABLES={"coverage":"S3-T00_coverage.csv","grid":"S3-T11_development_grid.csv",
    "folds":"S3-T12_development_fold_eligibility.csv","nominees":"S3-T13_development_nominees.csv",
    "decisions":"S3-T13_validation_decisions.csv","neighbors":"S3-T15_neighborhood_frontiers.csv",
    "final":"S3-T14_final_effects.csv","validation":"S3-T14_validation_effects.csv","recent":"S3-T14_recent_effects.csv",
    "horizons":"S3-T02_final_horizon_scorecard.csv"}
PUBLIC_HORIZONS=(1,15,30,100)
METHODS=("The 5m EMA20/50 cloud and Wilder ATR14 remain fixed. A 5m signal uses its completed current cloud; a 3m signal freezes the latest scheduled 5m cloud completed at its open. "
    "Every gateway has its own causal acceptance history, both directions, one selected-boundary signal per pullback and zero cooldown. Every selected penetration consumes the setup, including width or ATR rejection. Equality has no directional signal. "
    "The 192 streams comprise 12 product/candle/touch cells and 16 gateways each. The 2,688 development grid cells cover 14 frozen horizons. "
    "Selection uses H15 only, with equal weights on four 2019–2020 half-year event means of signed terminal movement divided by entry ATR. The guards require at least 200 pooled completed observations, 60 sessions and 20 weeks; each fold needs 25 completed observations and 10 sessions. Completed-support retention must be at least 20% of baseline, mean normalized MAE no greater than baseline, and mean normalized MFE at least 90% of baseline. Improvement must be positive overall and in at least three of four folds. "
    "Near ties are anchored to the greatest eligible score within relative 1e−12, then ordered by more completed observations, absolute before ATR, smaller within-family threshold and stable gateway ID. Undefined comparisons fail. Validation uses six 2021–2023 half-years, the same support and risk guards, positive pooled event improvement and at least four positive folds. Failure returns to the fixed baseline without another search. "
    "Only frozen choices and fixed baselines reach the 2024–2025 final evaluation and 2026 recent replication. The first 100 canonical scheduled slots of every development/validation half-year and each final/recent period are embargoed. Invalid scheduled slots count; closures add none. Horizons extending beyond an endpoint are purged. These masks never reset features or acceptance. "
    "Common scoring support requires finite positive entry ATR after independently generated acceptance. Candidate and baseline retain their own event populations; accepted timestamps are never intersected. Absolute full-support views remain separate. "
    "H counts following scheduled active chart slots and excludes the signal candle. Nominal duration is H×interval; actual elapsed time and closure crossings remain saved. H15 means 45 active minutes on 3m and 75 on 5m. The full horizon surface is descriptive, with no global holding-period optimizer or executable exit. "
    "Final primary comparisons are the 12 All-direction H15 event-weighted normalized terminal contrasts, selected minus fixed. Paired circular Monday calendar-week blocks use 10,000 draws and seed 20261010: four weeks primary, one/eight weeks sensitivity. Separate continuous period rosters retain zero-event weeks. "
    "Pointwise intervals have nominal 95% confidence. The 12-cell Bonferroni family uses exact tails 0.05/24 and 1−0.05/24, with nominal marginal confidence 99.5833333%. Identity fallbacks are zero only when estimable; undefined means and draws remain null. Session-balanced sensitivities average whole contributing sessions first and assign their trading date to Monday weeks. Validation and recent uncertainty are separately labeled and are not independent confirmation. "
    "Terminal signs are strict about zero. MFE>MAE uses tolerance 1e−10×max(1,MFE,MAE). Quantiles interpolate at p(n−1).")
QUALIFICATIONS=("The immutable 1.1.0 input extension uses unadjusted same-contract prices, independent 3m/5m aggregation and 250 consecutive usable 5m observations after unknown gaps or rolls. Known scheduled closures preserve state. "
    "The ES/NQ 16:15–16:30 New York pause applies only before trading-session date 2021-06-28. Uncertified holiday or short sessions remain unusable and reset feature history. Empty, mixed and partial slots are retained; prices are never filled. "
    "Readiness means usable AND feature-valid. It is an input support measure, independent of direction and future path completion. The annual table includes 2017 warmup; no 2010–2017 outcomes are computed. Missing no-trade minutes cannot reliably be distinguished from source loss. "
    "available_at is modeled completion. Original vendor receipt and mapping arrival times are absent, and the calendar is conservative rather than annually certified. Raw reconstruction, native TradingView replay/compilation and independent backup certification remain separate limitations. "
    "Early GC and other sparse cohorts require their exact session, week and event supports. Zero events do not imply zero opportunity in unknown coverage. Sparse means fewer than 100 completed observations or 30 contributing sessions. "
    "Earlier Abacus studies inspected later history, so these chronological reserved phases are not a pristine market holdout. Search folds are selection and stability evidence. Higher conditional means with fewer observations do not establish a better strategy. Reference closes, MFE/MAE and terminal deltas are observations, not simulated fills, costs, stops, targets or profits.")


def _identity(row):return (row["product"],int(row["interval_minutes"]),row["touch_mode"])


def _number(raw):return float(raw) if raw!="" else np.nan


def primary_rows(rows, kind="bonferroni12"):
    selected=[(i,r) for i,r in enumerate(rows,1) if r["direction"]=="All" and r["horizon"]=="15" and r["unit"]=="atr" and r["weighting"]=="event" and r["metric"]=="terminal_delta" and r["block_weeks"]=="4" and r["interval_kind"]==kind]
    if len(selected)!=12 or {_identity(r) for _,r in selected}!=set(CELLS):raise ValueError("complete twelve-cell primary family required")
    return selected


def headline(rows):
    family=primary_rows(rows)
    defined=[r for _,r in family if r["ci_low"]!="" and r["ci_high"]!=""]
    crossing=sum(_number(r["ci_low"])<=0<=_number(r["ci_high"]) for r in defined)
    positive=sum(_number(r["ci_low"])>0 for r in defined)
    negative=sum(_number(r["ci_high"])<0 for r in defined)
    return (f"The twelve prespecified final H15 comparisons have {crossing} adjusted intervals including zero, {positive} entirely above zero, {negative} entirely below zero and {12-len(defined)} undefined. "
            "These compare each frozen gateway’s own accepted observations with its fixed-width baseline; they do not establish executable profitability.")


def primary_claim(row):
    def f(key):return "undefined" if row[key]=="" else format(float(row[key]),".4f")
    kind="identity fallback" if row["identity_fallback"] in ("True","true") else "validated gateway"
    return (f"{row['product']} {row['interval_minutes']}m {row['touch_mode']}: {kind} {row['selected_gate_id']} versus {row['fixed_gate_id']}; final H15 normalized terminal difference {f('estimate')}, "
            f"four-week Bonferroni interval [{f('ci_low')}, {f('ci_high')}], selected/fixed completed ATR-valid observations {row['selected_evaluable']}/{row['fixed_evaluable']}, undefined draws {row['undefined_draws']}.")


def selection_summary(nominees,decisions,grid):
    nominated=[r for r in nominees if r['nomination_status']=='eligible_nominee']
    absolute=sum(r['selected_gate_family']=='absolute' for r in nominated)
    atr=sum(r['selected_gate_family']=='atr' for r in nominated)
    passes=sum(r['validation_passed'] in ('True','true') for r in decisions)
    failed=[r for r in decisions if r['validation_status']=='fixed_fallback_validation_failed']
    guard_counts={}
    for row in failed:
        for guard in row['failed_validation_guards'].split(';'):
            if guard:guard_counts[guard]=guard_counts.get(guard,0)+1
    guards=', '.join(f'{k}={v}' for k,v in sorted(guard_counts.items())) or 'none'
    h15=[r for r in grid if r['horizon']=='15']
    def extent(key):
        values=[float(r[key]) for r in h15 if r[key]!='']
        return f'[{min(values):.4f}, {max(values):.4f}]' if values else 'undefined'
    support=[int(r['evaluable']) for r in h15]
    return (f'Development produced {len(nominated)} eligible nominees: {absolute} absolute-width and {atr} ATR-ratio gateways; {12-len(nominated)} cells retained the fixed baseline because no candidate passed every guard. '
        f'Validation passed {passes} nominees and rejected {len(failed)} eligible development nominees. Final fixed fallbacks total {12-passes}. Failed validation guard counts among rejected nominees are {guards}; a nominee may fail multiple guards. '
        f'Across the 192 development H15 gateway cells, completed ATR-valid support ranges from {min(support)} to {max(support)}. Same-H fixed-baseline retention ranges {extent("retention")}, normalized terminal improvement {extent("difference_mean_terminal_delta")} and normalized mean MAE {extent("mean_mae")}. '
        'These ranges describe both gateway families and all failures; they do not select a global optimum. The exact grid, fold supports, guard failures and neighboring thresholds remain in the private saved tables.')


def _chosen(path,predicate):
    _,rows=read_csv(path)
    return [(i,r) for i,r in enumerate(rows,1) if predicate(r)]


def _columns(names,numeric=()):
    return [dict(key=n,label=n.replace("_"," ").title(),**({"format":"number","precision":4} if n in numeric else {})) for n in names]


def project_table(stage,path,selected,columns,identity,title,description):
    if len(selected)>100 or len(columns)>12:raise ValueError("bounded selected table budget")
    numeric={c["key"] for c in columns if "format" in c}
    rows=[{c["key"]:(float(raw[c["key"]]) if c["key"] in numeric else raw[c["key"]]) if raw[c["key"]]!="" else None for c in columns} for _,raw in selected]
    section=dict(id=identity,kind="table",title=title,description=description,columns=columns,rows=rows,notes=[])
    binding=dict(section_id=identity,source_path=path.relative_to(stage).as_posix(),source_sha256=sha256(path),
        source_rows=[i for i,_ in selected],row_ids=[r.get("row_id","") for _,r in selected],columns=[c["key"] for c in columns],numeric_columns=sorted(numeric))
    return section,binding


def project_download(stage,path,selected,names,identity,run_id):
    if not 1<=len(selected)<=1000 or len(names)>24:raise ValueError("bounded CSV download budget")
    destination=stage/"downloads"/(identity+".csv");destination.parent.mkdir(parents=True,exist_ok=True)
    with destination.open("w",newline="",encoding="utf-8") as stream:
        writer=csv.DictWriter(stream,fieldnames=names,lineterminator="\n");writer.writeheader();writer.writerows({k:r[k] for k in names} for _,r in selected)
    if destination.stat().st_size>256*1024:raise ValueError("CSV byte budget")
    source=path.relative_to(stage).as_posix()
    declaration=dict(id=identity,path=destination.relative_to(stage).as_posix(),label=identity.replace("-"," ").title(),description="Exact original saved summary strings; blanks remain undefined.",
        population="Stage 3 scoped independent acceptance populations; period and gateway columns identify each support.",units="Normalized ATR, product-specific raw points, counts and shares as named.",
        scope="Predeclared bounded summary projection; full grid/events remain private.",mediaType="text/csv",columns=names,rowCount=len(selected),sha256=sha256(destination),
        source=dict(runId=run_id,artifact=source,sha256=sha256(path)))
    binding=dict(download_id=identity,source_path=source,source_sha256=sha256(path),source_rows=[i for i,_ in selected],columns=names,
        download_path=destination.relative_to(stage).as_posix(),download_sha256=sha256(destination))
    return declaration,binding


def render_figures(stage,paths,choices):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size":8,"axes.titlesize":9,"axes.labelsize":8,"figure.facecolor":"white","axes.spines.top":False,"axes.spines.right":False})
    grids=pd.read_csv(paths["grid"]);neighbors=pd.read_csv(paths["neighbors"]);coverage=pd.read_csv(paths["coverage"])
    effects={p:pd.read_csv(paths[p]) for p in ("validation","final","recent")}
    figure_dir=stage/"figures";figure_dir.mkdir(parents=True,exist_ok=True)
    figures=[];bindings=[]
    def source(key,frame,columns):
        _,raw=read_csv(paths[key]);lookup={r["row_id"]:i for i,r in enumerate(raw,1)}
        return dict(path=paths[key].relative_to(stage).as_posix(),sha256=sha256(paths[key]),rows=[lookup[x] for x in frame.row_id],row_ids=frame.row_id.tolist(),columns=columns)
    def finish(fig,identity,title,caption,sources,panels=12):
        fig.suptitle(title,fontsize=14);fig.tight_layout(rect=(0,0,.93 if identity=='development_heatmaps' else 1,.97))
        path=figure_dir/(identity+".png");fig.savefig(path,dpi=125,pil_kwargs={"optimize":True});plt.close(fig)
        if path.stat().st_size>2*1024*1024:raise ValueError("figure byte budget")
        rel=path.relative_to(stage).as_posix()
        figures.append(dict(id=identity.replace("_","-"),kind="figure",title=title,path=rel,alt=f"{title}; {panels} product/candle/touch panels; undefined support remains visibly missing.",caption=caption))
        bindings.append(dict(path=rel,sha256=sha256(path),sources=sources))
    def cell(frame,c):
        p,i,b=c;return frame.loc[frame['product'].eq(p)&frame.interval_minutes.eq(i)&frame.touch_mode.eq(b)]
    def axes():return plt.subplots(3,4,figsize=(16,10))
    fig,axs=axes();lim=max(.01,float(grids.difference_mean_terminal_delta.abs().quantile(.98)))
    for ax,c in zip(axs.flat,CELLS):
        part=cell(grids,c).copy();part['order']=part.gate_family.map({'absolute':0,'atr':1})
        part=part.sort_values(['order','gate_threshold','horizon']);gates=part.gate_id.drop_duplicates().tolist();hs=sorted(part.horizon.unique())
        values=part.pivot(index='gate_id',columns='horizon',values='difference_mean_terminal_delta').reindex(gates).reindex(columns=hs).to_numpy(float)
        im=ax.imshow(np.ma.masked_invalid(values),aspect='auto',cmap='RdBu_r',vmin=-lim,vmax=lim)
        ax.set_title(f'{c[0]} {c[1]}m {c[2]}');ax.set_xticks(range(len(hs)),hs,rotation=45);ax.set_yticks(range(len(gates)),gates,fontsize=6);ax.set_xlabel('Scheduled active bars H')
    cax=fig.add_axes([.945,.23,.012,.55]);fig.colorbar(im,cax=cax,label='Normalized terminal improvement vs same-H fixed baseline')
    finish(fig,'development_heatmaps','Development terminal surfaces',"All 192 gateways × 14 horizons; own accepted populations on common finite-positive entry ATR support. Color limits are shared and clip the outer 2% for readability; exact values remain in private S3-T11. This is a descriptive surface, not a horizon optimizer.",[source('grid',grids,['gate_id','gate_family','gate_threshold','horizon','difference_mean_terminal_delta'])])
    fig,axs=axes();h15=grids.loc[grids.horizon.eq(15)]
    for ax,c in zip(axs.flat,CELLS):
        part=cell(h15,c);nb=cell(neighbors,c);nb=nb.loc[nb.horizon.eq(15)]
        for family,marker,color in (('absolute','o','#2171b5'),('atr','s','#d95f0e')):
            g=part.loc[part.gate_family.eq(family)];ax.scatter(g.retention,g.difference_mean_terminal_delta,s=28,marker=marker,c=color,label=family)
            for r in g.itertuples():ax.annotate(r.gate_id,(r.retention,r.difference_mean_terminal_delta),fontsize=5,xytext=(3,2),textcoords='offset points')
        frontier=nb.loc[nb.pareto_frontier.eq(True)];ax.scatter(frontier.retention,frontier.difference_mean_terminal_delta,s=75,facecolors='none',edgecolors='#111',label='Pareto frontier')
        ax.axhline(0,color='#aaa',lw=.7);ax.axvline(.2,color='#aaa',lw=.7,ls=':');ax.set_title(f'{c[0]} {c[1]}m {c[2]}');ax.set_xlabel('Completed-support retention vs fixed');ax.set_ylabel('H15 normalized terminal improvement')
    axs.flat[0].legend(fontsize=6)
    finish(fig,'retention_risk_frontiers','Conditional quality and opportunity retention',"H15 development counts stay gateway-specific. Outlined points are nondominated across all 16 gateways in each cell in retention, normalized terminal mean and normalized MAE; risk enters the saved frontier definition. Dotted 20% retention is only one selection guard; no plotted point implies a profitable strategy.",[source('grid',h15,['gate_id','horizon','retention','difference_mean_terminal_delta','mean_mae']),source('neighbors',neighbors.loc[neighbors.horizon.eq(15)],['pareto_frontier','gate_family','retention','mean_terminal_delta','mean_mae'])])
    fig,axs=axes();horizon_inputs=[]
    for ax,c in zip(axs.flat,CELLS):
        choice=choices[c];part=cell(grids,c);chosen=part.loc[part.gate_id.eq(choice['nominee_gate_id'])].sort_values('horizon');base=part.loc[part.gate_id.eq(choice['fixed_gate_id'])].sort_values('horizon');horizon_inputs.extend([chosen,base])
        for metric,color in (('mfe','#2171b5'),('mae','#d95f0e'),('terminal_delta','#6a3d9a')):
            ax.plot(chosen.horizon,chosen['mean_'+metric],color=color,label='nominee '+metric)
            ax.plot(base.horizon,base['mean_'+metric],color=color,ls=':',alpha=.7,label='fixed '+metric)
        ax.axhline(0,color='#aaa',lw=.6);ax.set_title(f"{c[0]} {c[1]}m {c[2]} · {choice['nominee_gate_id']}");ax.set_xlabel('Active chart bars H');ax.set_ylabel('Entry ATR units')
    axs.flat[0].legend(fontsize=5,ncol=2)
    finish(fig,'horizon_response','Frozen development nominee horizon response',"Solid lines show the development nominee (or fixed fallback); dotted lines show the fixed same-touch baseline. MFE/MAE are positive path excursions and terminal movement is signed. These 14 horizons are descriptive; no holding period is selected and 3m/5m H values represent different active durations.",[source('grid',pd.concat(horizon_inputs).drop_duplicates('row_id'),['gate_id','horizon','horizon_minutes','mean_mfe','mean_mae','mean_terminal_delta'])])
    fig,axs=axes();h15n=neighbors.loc[neighbors.horizon.eq(15)]
    for ax,c in zip(axs.flat,CELLS):
        part=cell(h15n,c)
        for family,color in (('absolute','#2171b5'),('atr','#d95f0e')):
            g=part.loc[part.gate_family.eq(family)].sort_values('gate_threshold');x=np.arange(len(g))
            ax.plot(x,g.difference_mean_terminal_delta,marker='o',color=color,label=family)
            stable=g.stable_positive_neighborhood.eq(True);ax.scatter(x[stable],g.loc[stable,'difference_mean_terminal_delta'],s=75,facecolors='none',edgecolors=color)
        ax.axhline(0,color='#aaa',lw=.7);ax.set_title(f'{c[0]} {c[1]}m {c[2]}');ax.set_xticks(range(8),range(1,9));ax.set_xlabel('Increasing threshold rank within each family');ax.set_ylabel('H15 normalized terminal improvement')
    axs.flat[0].legend(fontsize=6)
    finish(fig,'neighborhood_stability','Adjacent-gateway stability',"Ranks 1–8 are ordered separately within the absolute and ATR families and are not equivalent units. Outlined points have a positive candidate-plus-adjacent neighborhood; endpoints have one neighbor. All values are development-only descriptive diagnostics, not additional selection gates.",[source('neighbors',h15n,['gate_family','gate_threshold','difference_mean_terminal_delta','neighbor_count','neighbor_min_improvement','stable_positive_neighborhood'])])
    fig,axs=axes();eval_sources=[]
    for ax,c in zip(axs.flat,CELLS):
        visible=[]
        for x,p in enumerate(('validation','final','recent')):
            g=cell(effects[p],c);g=g.loc[g.horizon.eq(15)&g.direction.eq('All')&g.unit.eq('atr')&g.metric.eq('terminal_delta')&g.weighting.eq('event')&g.block_weeks.eq(4)]
            point=g.loc[g.interval_kind.eq('pointwise95')]
            if len(point)!=1:raise ValueError('one saved pooled H15 interval per evaluation cell')
            r=point.iloc[0]
            visible.extend(float(v) for v in (r.estimate,r.ci_low,r.ci_high) if np.isfinite(v))
            if np.isfinite(r.estimate):
                ax.plot(x,r.estimate,'o',color='#2171b5');ax.vlines(x,r.ci_low,r.ci_high,color='#2171b5',lw=2)
            else:ax.annotate('undefined',(x,0),rotation=90,fontsize=7)
            if p=='final':
                f=g.loc[g.interval_kind.eq('bonferroni12')].iloc[0];visible.extend(float(v) for v in (f.ci_low,f.ci_high) if np.isfinite(v));ax.vlines(x+.12,f.ci_low,f.ci_high,color='#d95f0e',lw=3)
            ax.annotate(f"S/F {int(r.selected_evaluable)}/{int(r.fixed_evaluable)}",(x,0),xytext=(0,-28),textcoords='offset points',ha='center',fontsize=5)
            eval_sources.append(source(p,g,['estimate','ci_low','ci_high','interval_kind','selected_evaluable','fixed_evaluable','identity_fallback']))
        ax.axhline(0,color='#999',lw=.7);ax.set_title(f'{c[0]} {c[1]}m {c[2]}');ax.set_xticks(range(3),['Validation','Final','Recent'],rotation=15);ax.set_xlim(-.4,2.4);ax.set_ylabel('Selected − fixed terminal / entry ATR')
        low,high=min([0.]+visible),max([0.]+visible);span=max(.1,high-low);ax.set_ylim(low-.2*span,high+.2*span)
    finish(fig,'frozen_choice_evaluation','Sequential frozen-choice evaluation',"Blue intervals are pooled H15 nominal 95% pointwise four-week results; orange final intervals use the 12-cell Bonferroni adjustment. Validation compares the frozen nominee before fallback decisions; final/recent compare the frozen final choice. S/F denotes separate selected/fixed completed ATR-valid observations. Identity fallbacks and undefined populations are retained.",eval_sources)
    fig,axs=plt.subplots(3,2,figsize=(14,10))
    for ax,(p,i) in zip(axs.flat,((p,i) for p in ('ES','GC','NQ') for i in (3,5))):
        g=coverage.loc[coverage['product'].eq(p)&coverage.interval_minutes.eq(i)].sort_values('year')
        ax.plot(g.year,g.ready_share,marker='o',label='Mapped feature readiness',color='#2171b5')
        ax.plot(g.year,g.usable_share,marker='s',label='Usable chart-slot share',color='#555',ls=':')
        ax.set_title(f'{p} {i}m · 2017 warmup; 2026 partial year');ax.set_ylim(0,1.03);ax.set_xlim(2016.7,2026.3);ax.set_xticks(range(2017,2027));ax.tick_params(axis='x',rotation=45);ax.set_ylabel('Share of canonical scheduled chart slots')
        for r in g.itertuples():ax.annotate(f'{int(r.ready_sessions)}s',(r.year,r.ready_share),fontsize=6,xytext=(0,5),textcoords='offset points',ha='center')
    axs.flat[0].legend(fontsize=7)
    finish(fig,'calendar_coverage','Input coverage and mapped readiness',"Readiness is count(usable AND feature_valid)/scheduled slots for each interval; labels show distinct ready sessions. Equality and future paths do not enter readiness. Uncertified sessions remain unusable, 2017 is warmup-only and 2026 stops at the retained September 18 endpoint. Zero events never establish full opportunity coverage.",[source('coverage',coverage,['year','scheduled_slots','usable_slots','feature_ready_slots','mapped_ready_slots','ready_share','usable_share','ready_sessions'])],panels=6)
    if sum((stage/b['path']).stat().st_size for b in bindings)>8*1024*1024:raise ValueError('combined figure budget')
    save_json(stage/'provenance/figure-environment.json',_figure_environment())
    return figures,bindings


def render_bundle(stage,run_id=None):
    stage=Path(stage).resolve();run_id=run_id or stage.name
    if any((stage/name).exists() for name in ("publication.json","source-bindings.json","report.md","report.html","advice.md")):
        raise ValueError("retained Stage 3 presentation overwrite refused")
    paths={k:stage/'tables'/v for k,v in TABLES.items()}
    absent=[str(p) for p in paths.values() if not p.is_file()]
    if absent:raise ValueError('essential saved Stage 3 report evidence absent: '+', '.join(absent))
    _,final=read_csv(paths['final']);_,decisions=read_csv(paths['decisions']);choices={_identity(r):r for r in decisions}
    if set(choices)!=set(CELLS) or len(decisions)!=12:raise ValueError('complete frozen final choice family')
    primary=primary_rows(final);claims=[primary_claim(r) for _,r in primary];finding=headline(final)
    _,nominees=read_csv(paths['nominees']);_,grid=read_csv(paths['grid']);selection_text=selection_summary(nominees,decisions,grid)
    sections=[dict(id='findings',kind='text',title='Final primary findings',body=finding+'\n\n'+'\n\n'.join(claims)),
        dict(id='selection-results',kind='text',title='Development families, nominations and validation failures',body=selection_text),
        dict(id='selection-method',kind='text',title='Frozen search, masks and sequential decisions',body=METHODS),
        dict(id='limitations',kind='text',title='Input support and interpretation limits',body=QUALIFICATIONS)]
    bindings=[];claim_bindings=[]
    for (i,r),text in zip(primary,claims):
        claim_bindings.append(dict(section_id='findings',text=text,source_path=paths['final'].relative_to(stage).as_posix(),source_sha256=sha256(paths['final']),source_row=i,
            values={k:r[k] for k in ('product','interval_minutes','touch_mode','estimate','ci_low','ci_high','selected_gate_id','fixed_gate_id','identity_fallback','selected_evaluable','fixed_evaluable','undefined_draws')}))
    def table(key,selection,identity,title,names,numeric,description):
        section,binding=project_table(stage,paths[key],selection,_columns(names,numeric),identity,title,description);sections.append(section);bindings.append(binding)
    table('final',primary,'primary-final','Twelve final adjusted effects',['product','interval_minutes','touch_mode','selected_gate_id','estimate','ci_low','ci_high','selected_evaluable','fixed_evaluable','undefined_draws'],('estimate','ci_low','ci_high'),
        'All-direction H15 event normalized terminal contrasts; four-week 12-cell Bonferroni intervals. Identity/null fallbacks retain the full family; separate branch populations are never intersected.')
    _,finalrows=read_csv(paths['final'])
    sensitivities=[(i,r) for i,r in enumerate(finalrows,1) if r['horizon']=='15' and r['direction']=='All' and r['unit']=='atr' and r['metric']=='terminal_delta' and r['weighting']=='event' and r['interval_kind'] in ('pointwise95','bonferroni12')]
    table('final',sensitivities,'primary-sensitivity','Final primary uncertainty sensitivities',['product','interval_minutes','touch_mode','block_weeks','interval_kind','estimate','ci_low','ci_high','defined_draws','undefined_draws'],('estimate','ci_low','ci_high'),
        'Four-week blocks are primary. One/eight-week and pointwise results remain sensitivities; nominal confidence levels do not guarantee bootstrap coverage.')
    table('decisions',list(enumerate(decisions,1)),'choices','Development nominees and validation fallback',['product','interval_minutes','touch_mode','nominee_gate_id','nomination_status','eligible_candidates','validation_status','failed_validation_guards','selected_gate_id','fallback'],(),
        'Exactly one nominee/fallback per cell. Only these validation decisions define final/recent gateways; failed candidates are never searched again.')
    for p in ('validation','recent'):
        _,rows=read_csv(paths[p]);chosen=primary_rows(rows,'pointwise95')
        table(p,chosen,'effects-'+p,p.title()+' frozen effects',['product','interval_minutes','touch_mode','selected_gate_id','estimate','ci_low','ci_high','selected_evaluable','fixed_evaluable','undefined_draws'],('estimate','ci_low','ci_high'),
            'Pooled H15 All ATR event four-week nominal 95% pointwise results. Validation describes the nominee before its decision; recent replicates the frozen final choice. These are separately labeled evidence phases.')
    selected_horizons=_chosen(paths['horizons'],lambda r:r['direction']=='All' and r['unit']=='atr' and r['support']=='common_atr_valid' and r['gate_id']==choices[_identity(r)]['selected_gate_id'])
    for b in ('fast','slow'):
        table('horizons',[(i,r) for i,r in selected_horizons if r['touch_mode']==b and int(r['horizon']) in PUBLIC_HORIZONS],'horizons-'+b,'Final frozen '+b+' selected descriptive horizons',
            ['product','interval_minutes','horizon','horizon_minutes','gate_id','completed','censored','contributing_sessions','mean_mfe','mean_mae','mean_terminal_delta','mean_elapsed_minutes'],('mean_mfe','mean_mae','mean_terminal_delta','mean_elapsed_minutes'),
            'Predeclared descriptive snapshots H1, H15, H30 and H100. All 14 frozen horizons remain in the selected-horizon CSV and private full scorecard. Entry-ATR-normalized excursions and signed terminal means retain separate elapsed minutes. No horizon is selected for execution.')
    figures,figure_bindings=render_figures(stage,paths,choices);sections.extend(figures)
    baselines={'stage1':'20261010T221954Z_s1_8c6e_r3','stage2':'20261011T002602Z_s2_c1b4'}
    baseline_text=('Fixed fast/slow scientific reproduction is retained separately at the original 2018–2020 endpoint and original horizons; new fold masks are not applied to that parity gate. '
        f"Stage 1 {baselines['stage1']} and Stage 2 {baselines['stage2']} remain immutable. Their pooled primary intervals included zero; mean MAE exceeded mean MFE in the fixed pooled cells. "
        'Side/session and block sensitivities differ, and early GC support is sparse. The extended release must reproduce every original mapped scientific prefix and every old fixed state/event/path/table estimand, including old endpoint censors. Maintained verifier/presentation repairs remain distinct from executed snapshots.')
    sections.extend([dict(id='baselines',kind='text',title='Preserved baseline attribution and exact parity',body=baseline_text),
        dict(id='advice',kind='text',title='Dated research advice',body=finding+'\n\nRetain each saved development nomination and validation decision, including failures. Assess event counts, session-balanced sensitivities, neighboring gateways and normalized MAE/MFE together. A validated gateway is a conditional path finding; implementation as a trading policy requires a separately specified execution/cost/risk study. Do not promote a descriptive holding horizon to an executable exit.'),
        dict(id='evidence',kind='text',title='Evidence and reproducibility',body='Full private S3-T11–T16 search/folds/masks, complete failure guards, gate technical/events/outcomes, quantiles, annual/session/hour/week/month support, weekly sufficient statistics, input-prefix/fixed parity, sequential freeze receipts and independent state/path/selection/uncertainty/transfer checks are retained. Every displayed cell/claim/figure/download binds to saved bytes. Publication validation checks selected presentation and assets; it does not reproduce research. No public staging, catalog change or deployment is part of this run.')])
    downloads=[];download_bindings=[]
    _,covrows=read_csv(paths['coverage'])
    specs=[('final',sensitivities,'primary-effects',['row_id','period_id','product','interval_minutes','touch_mode','selected_gate_id','fixed_gate_id','block_weeks','interval_kind','estimate','ci_low','ci_high','ci_level','selected_evaluable','fixed_evaluable','selected_sessions','fixed_sessions','identity_fallback','defined_draws','undefined_draws','sparse_warning']),
        ('decisions',list(enumerate(decisions,1)),'frozen-choices',['row_id','product','interval_minutes','touch_mode','nominee_gate_id','fixed_gate_id','eligible_candidates','nomination_status','selection_score','selection_improvement','validation_status','validation_passed','failed_validation_guards','validation_improvement','selected_gate_id','selected_gate_family','selected_gate_threshold','fallback']),
        ('horizons',selected_horizons,'selected-horizon-scorecard',['row_id','period_id','product','interval_minutes','touch_mode','gate_id','horizon','horizon_minutes','accepted_total','accepted','completed','censored','evaluable','contributing_sessions','contributing_weeks','mean_mfe','mean_mae','mean_terminal_delta','session_mean_terminal_delta','favorable_share','mfe_gt_mae_share','mean_elapsed_minutes','sparse_warning']),
        ('coverage',list(enumerate(covrows,1)),'coverage-support',['row_id','product','interval_minutes','year','scope','scheduled_slots','usable_slots','calendar_uncertified_slots','feature_ready_slots','mapped_ready_slots','atr_valid_slots','ready_share','usable_share','unknown_signal_slots','contributing_sessions','ready_sessions','first_timestamp','last_available_at','coverage_complete'])]
    for key,selection,identity,names in specs:
        d,b=project_download(stage,paths[key],selection,names,identity,run_id);downloads.append(d);download_bindings.append(b)
    if sum((stage/d['path']).stat().st_size for d in downloads)>512*1024:raise ValueError('combined download bytes')
    publication=dict(schemaVersion='1.1',id='ema-cloud-stage3-'+run_id.lower().replace('_','-'),title='20/50 5minEMA Cloud Trend Follow Opportunity Study — Stage 3',summary=finding,
        publishedAt=datetime.strptime(run_id[:16],'%Y%m%dT%H%M%SZ').strftime('%Y-%m-%dT%H:%M:%SZ'),source=dict(producer='Sahadeva',runId=run_id),sections=sections,downloads=downloads)
    (stage/'publication.json').write_text(json.dumps(publication,ensure_ascii=False,separators=(',',':'),allow_nan=False)+'\n',encoding='utf-8')
    if (stage/'publication.json').stat().st_size>96*1024:raise ValueError('private Narada source budget')
    workspace=Path(__file__).resolve().parents[3]
    baseline_sources=[dict(run_id=rid,path=str(workspace/'runs'/STUDY_ID/rid/name),sha256=sha256(workspace/'runs'/STUDY_ID/rid/name)) for rid in baselines.values() for name in ('manifest.json','protocol.md','config.json','report.md','advice.md')]
    save_json(stage/'source-bindings.json',dict(schema_version='study21.stage3-source/v1',run_id=run_id,publication_sha256=sha256(stage/'publication.json'),cells=bindings,claims=claim_bindings,downloads=download_bindings,figures=figure_bindings,
        selection_claim=dict(text=selection_text,sources=[dict(path=paths[k].relative_to(stage).as_posix(),sha256=sha256(paths[k])) for k in ('nominees','decisions','grid')]),
        aggregate_claim=dict(text=finding,source_path=paths['final'].relative_to(stage).as_posix(),source_sha256=sha256(paths['final']),source_rows=[i for i,_ in primary]),baseline_sources=baseline_sources,
        qualification='Cross-run baseline attribution remains a private byte locator; public saved-artifact references identify this run only.'))
    md=['# '+publication['title'],f'Run {run_id} · development 2018–2020; validation 2021–2023; final 2024–2025; recent 2026 through September 18']
    body=['<h1>'+html.escape(publication['title'])+'</h1>','<p>'+html.escape(md[1])+'</p>']
    for s in sections:
        md.extend(['','## '+s['title'],'']);body.append('<section id="'+s['id']+'"><h2>'+html.escape(s['title'])+'</h2>')
        if s['kind']=='text':md.append(s['body']);body.extend('<p>'+html.escape(p)+'</p>' for p in s['body'].split('\n\n'))
        elif s['kind']=='figure':md.extend([f"![{s['alt']}]({s['path']})",s['caption']]);body.append('<figure><img src="'+s['path']+'" alt="'+html.escape(s['alt'],quote=True)+'"><figcaption>'+html.escape(s['caption'])+'</figcaption></figure>')
        else:
            keys=[c['key'] for c in s['columns']];md.extend([s['description'],'','| '+' | '.join(c['label'] for c in s['columns'])+' |','| '+' | '.join('---' for _ in keys)+' |']);md.extend('| '+' | '.join('undefined' if r[k] is None else str(r[k]) for k in keys)+' |' for r in s['rows']);body.extend(['<p>'+html.escape(s['description'])+'</p>',_html_table(s['columns'],s['rows'])])
        body.append('</section>')
    links=sorted((stage/'tables').glob('*.csv'))
    md.extend(['','## Exact saved tables','']+[f'- [{p.name}](tables/{p.name})' for p in links]);body.append('<h2>Exact saved tables</h2><ul>'+''.join('<li><a href="tables/'+p.name+'">'+p.name+'</a></li>' for p in links)+'</ul>')
    (stage/'report.md').write_text('\n'.join(md)+'\n',encoding='utf-8')
    (stage/'report.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>EMA Cloud Stage3</title><style>body{font:16px/1.55 system-ui;max-width:1280px;margin:auto;padding:30px;color:#17233b}h1{line-height:1.2}h2{margin-top:2em}.scroll{overflow-x:auto}table{border-collapse:collapse;font-size:13px;min-width:700px}th,td{padding:7px 10px;border-bottom:1px solid #dde3ec;text-align:left}th{background:#edf2f8}img{max-width:100%;height:auto}figcaption{font-size:14px;color:#526076}a{color:#1c55b2}</style><body>'+'\n'.join(body)+'</body></html>\n',encoding='utf-8')
    (stage/'advice.md').write_text('# Stage 3 dated research advice\n\nRun '+run_id+' · '+publication['publishedAt'][:10]+'\n\n'+finding+'\n\n'+selection_text+'\n\n'+'\n\n'.join(claims)+'\n\n'+baseline_text+'\n\n'+QUALIFICATIONS+'\n\nNo descriptive horizon is an executable exit. Keep validation failures and fixed fallbacks. Higher conditional means with fewer observations do not establish better trading performance.\n',encoding='utf-8')
    return dict(status='rendered',sections=len(sections),figures=len(figures),claims=len(claims),downloads=len(downloads),publication_sha256=sha256(stage/'publication.json'),bindings_sha256=sha256(stage/'source-bindings.json'))
