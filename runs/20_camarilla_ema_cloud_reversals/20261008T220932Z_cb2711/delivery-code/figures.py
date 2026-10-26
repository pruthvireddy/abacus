#!/usr/bin/env python3
"""Render scientific figures exclusively from saved summary tables."""
import argparse
import csv
import json
import os
from pathlib import Path
os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/abacus-study20-matplotlib")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

def rows(work,name):
    with (work/"tables"/(name+".csv")).open() as f:return list(csv.DictReader(f))

def num(row,key):
    v=row.get(key,"")
    return float(v) if v not in ("",None) else np.nan

def main():
    p=argparse.ArgumentParser();p.add_argument("--work",type=Path,required=True);a=p.parse_args();w=a.work
    d=w/"figures";d.mkdir(exist_ok=True)
    plt.rcParams.update({"font.size":10,"axes.spines.top":False,"axes.spines.right":False,"figure.facecolor":"#f7f7f4","axes.facecolor":"#f7f7f4","savefig.facecolor":"#f7f7f4"})
    products=("ES","NQ","GC");colors={"none":"#727980","alignment":"#207b74"}
    horizons=rows(w,"horizons")
    fig,axs=plt.subplots(1,3,figsize=(13,4.4),sharey=True)
    for product,ax in zip(products,axs):
        for mode in colors:
            g=[r for r in horizons if r["product"]==product and r["split"]=="final_evaluation" and r["pair"]=="3" and r["mode"]==mode and r["side"]=="both" and num(r,"horizon")>0]
            x=np.array([num(r,"elapsed_minutes") for r in g]);y=np.array([num(r,"mean_delta") for r in g])
            ax.plot(x,y,"o-",color=colors[mode],label=mode)
            ax.fill_between(x,[num(r,"ci95_low") for r in g],[num(r,"ci95_high") for r in g],color=colors[mode],alpha=.15)
            if mode=="alignment":
                ax.plot(x,[num(r,"delta_median") for r in g],":",color="#207b74",label="alignment median delta")
                ax.plot(x,[num(r,"mean_MFE") for r in g],"--",color="#5575a7",label="alignment mean MFE")
                ax.plot(x,[-num(r,"mean_MAE") for r in g],"--",color="#ab6558",label="alignment negative MAE")
                for xx,yy,r in zip(x,y,g):ax.annotate("N="+r["completed_N"],(xx,yy),xytext=(0,10),textcoords="offset points",fontsize=7)
        ax.axhline(0,color="#888",linewidth=.7);ax.set_title(product);ax.set_xlabel("Elapsed minutes / entry bar counts as 1")
    axs[0].set_ylabel("ATR14 at confirmation");axs[-1].legend(fontsize=8)
    fig.suptitle("F01 · R3/S3 paths, final evaluation 2024–2025 · T01 · 95% block intervals");fig.tight_layout();fig.savefig(d/"horizons.png",dpi=140);plt.close(fig)
    fig,all_axs=plt.subplots(2,3,figsize=(13,9),sharey=True)
    for product,side,ax in [(product,side,all_axs[j,i]) for j,side in enumerate(("long","short")) for i,product in enumerate(products)]:
        g=[r for r in horizons if r["product"]==product and r["split"]=="final_evaluation" and r["side"]==side and num(r,"horizon")==15]
        for i,r in enumerate(g):
            y=num(r,"mean_delta");lo=num(r,"ci95_low");hi=num(r,"ci95_high")
            ax.errorbar(y,i,xerr=[[max(0,y-lo)],[max(0,hi-y)]],fmt="o",color=colors.get(r["mode"],"#5575a7"),capsize=2)
            ax.text(.99,i,"N="+r["completed_N"]+("*" if r["sparse"]=="True" else ""),transform=ax.get_yaxis_transform(),ha="right",va="center",fontsize=7,bbox={"facecolor":"#f7f7f4","alpha":.85,"edgecolor":"none","pad":1})
        ax.set_yticks(range(len(g)),["R"+r["pair"]+"/S"+r["pair"]+" · "+r["mode"] for r in g],fontsize=8)
        ax.axvline(0,color="#888",linewidth=.7);ax.set_xlabel("Mean signed delta / ATR");ax.set_title(product+" · "+side)
    fig.suptitle("F02 · 15-bar level/cloud grid · T01 · * sparse; absent interval = undefined CI");fig.tight_layout();fig.savefig(d/"cloud_grid.png",dpi=140);plt.close(fig)
    joint=rows(w,"joint_excursions");fig,axs=plt.subplots(1,3,figsize=(13,4.5))
    for product,ax in zip(products,axs):
        g=[r for r in joint if r["product"]==product];matrix=np.array([num(r,"N") for r in g]).reshape(6,6)
        im=ax.imshow(matrix.T,origin="lower",cmap="BuGn",aspect="auto",vmin=0,vmax=max(num(r,"N") for r in joint))
        for i,j in np.ndindex(6,6):ax.text(i,j,str(int(matrix[i,j])),ha="center",va="center",fontsize=8,color="white" if matrix[i,j]>max(num(r,"N") for r in joint)*.5 else "#222")
        labels=("0–.5",".5–1","1–2","2–3","3–5","5+");ax.set_xticks(range(6),labels);ax.set_yticks(range(6),labels);ax.set_xlabel("MAE / ATR");ax.set_ylabel("MFE / ATR");ax.set_title(product+" · N="+str(int(matrix.sum())))
    fig.suptitle("F03 · Joint excursions, R3/S3 alignment, 15 bars, 2024–2025 · T12");fig.tight_layout();fig.savefig(d/"joint_excursions.png",dpi=140);plt.close(fig)
    ordering=rows(w,"threshold_ordering");fig,axs=plt.subplots(1,3,figsize=(13,4.5),sharey=True)
    cats=("favorable_first","adverse_first","same_minute_ambiguous","neither","censored","entry_cancelled")
    palette=("#207b74","#ab6558","#d69a44","#8198b7","#bbbbbb","#555555")
    for product,ax in zip(products,axs):
        g=[r for r in ordering if r["product"]==product and r["split"]=="final_evaluation" and r["pair"]=="3" and r["mode"]=="alignment" and num(r,"horizon")==15]
        bottom=np.zeros(3)
        for cat,color in zip(cats,palette):
            vals=np.array([num(r,cat)/max(1,num(r,"accepted")) for r in g]);ax.bar(range(3),vals,bottom=bottom,color=color,label=cat.replace("_"," "));bottom+=vals
        ax.set_xticks(range(3),[r["favorable_threshold_ATR"]+" ATR" for r in g]);ax.set_title(product);ax.set_xlabel("Favorable threshold vs adverse 1 ATR")
    axs[0].set_ylabel("Share of accepted opportunities");fig.legend(*axs[-1].get_legend_handles_labels(),fontsize=7,ncol=3,loc="lower center",bbox_to_anchor=(.5,0))
    fig.suptitle("F04 · First threshold ordering at one minute · T09 · 15 bars, 2024–2025");fig.tight_layout(rect=(0,.1,1,1));fig.savefig(d/"threshold_ordering.png",dpi=140);plt.close(fig)
    annual=rows(w,"annual");fig,axs=plt.subplots(1,3,figsize=(13,4.5),sharey=True)
    for product,ax in zip(products,axs):
        g=[r for r in annual if r["product"]==product and r["pair"]=="3" and r["mode"]=="alignment" and r["side"]=="both"]
        x=[num(r,"year") for r in g];y=np.array([num(r,"mean_delta") for r in g]);lo=np.array([num(r,"ci95_low") for r in g]);hi=np.array([num(r,"ci95_high") for r in g])
        ax.errorbar(x,y,yerr=np.maximum(0,np.array([y-lo,hi-y])),fmt="o-",color="#207b74",capsize=2)
        ax.scatter([num(r,"year") for r in g if r["sparse"]=="True"],[num(r,"mean_delta") for r in g if r["sparse"]=="True"],marker="x",color="#333",s=20,zorder=3)
        ax.set_xlim(2009.5,2026.5);ax.axhline(0,color="#888",linewidth=.7);ax.axvspan(2023.5,2025.5,color="#dcb65b",alpha=.15);ax.set_title(product);ax.set_xlabel("Year (2026 ends September 18)")
    axs[0].set_ylabel("Mean signed delta / ATR");fig.suptitle("F05 · Annual R3/S3 alignment · T04 · final shaded; x sparse, counts/coverage in T04");fig.tight_layout();fig.savefig(d/"annual_stability.png",dpi=140);plt.close(fig)
    policies=rows(w,"policy");daily=rows(w,"daily_reference");fig,all_axs=plt.subplots(2,3,figsize=(13,8.5),sharey="row")
    axs=all_axs[0]
    for product,ax in zip(products,axs):
        for mode in colors:
            for slip in (0,1,2):
                g=[r for r in policies if r["product"]==product and r["split"]=="final_evaluation" and r["pair"]=="3" and r["mode"]==mode and r["extension"]=="core" and r["target"]=="3R" and num(r,"delay")==0 and r["touch"]=="False" and r["window"]=="main" and r["order_assumption"]=="stop_first" and num(r,"slippage_ticks")==slip]
                g=sorted(g,key=lambda r:num(r,"fee_USD"));ax.plot([num(r,"fee_USD") for r in g],[num(r,"mean_net_R_per_session") for r in g],marker="o",linestyle=(":","-","--")[slip],color=colors[mode],label=mode+f" · {slip} tick")
        ax.axhline(0,color="#888",linewidth=.7);ax.set_title(product);ax.set_xlabel("Assumed round-trip fees / USD")
    axs[0].set_ylabel("Mean net R / scorable eligible session");axs[-1].legend(fontsize=7)
    for product,ax in zip(products,all_axs[1]):
        for mode in colors:
            for assumption in ("stop_first","target_first"):
                g=[r for r in daily if r["product"]==product and r["split"]=="final_evaluation" and r["mode"]==mode and r["order_assumption"]==assumption]
                g=sorted(g,key=lambda r:r["day"]);vals=np.array([num(r,"net_R") for r in g]);curve=np.cumsum(np.nan_to_num(vals,nan=0));curve[~np.isfinite(vals)]=np.nan
                ax.plot(range(len(g)),curve,color=colors[mode],linestyle="-" if assumption=="stop_first" else "--",alpha=.8,label=mode+" · "+assumption)
        ax.axhline(0,color="#888",linewidth=.7);ax.set_xlabel("Eligible session sequence / gaps unresolved")
    all_axs[1,0].set_ylabel("Cumulative resolved-session net R");all_axs[1,-1].legend(fontsize=7)
    fig.suptitle("F06 · Policy costs and observed daily accumulation · T03/T13 · 3R, 2024–2025");fig.tight_layout();fig.savefig(d/"policy_costs.png",dpi=140);plt.close(fig)
    fig,axs=plt.subplots(1,3,figsize=(13,4.5),sharey=True)
    for product,ax in zip(products,axs):
        g=[r for r in horizons if r["product"]==product and r["split"]=="final_evaluation" and r["pair"]=="3" and r["mode"]=="alignment" and r["side"]=="both" and num(r,"horizon")>0]
        for metric,color in (("mae","#ab6558"),("mfe","#207b74")):
            for quantile,style in (("median","-"),("q75","--"),("q90",":")):
                ax.plot([num(r,"elapsed_minutes") for r in g],[num(r,metric+"_"+quantile) for r in g],style,color=color,label=metric+" "+quantile)
        ax.set_title(product);ax.set_xlabel("Elapsed minutes")
    axs[0].set_ylabel("Excursion magnitude / ATR14");axs[-1].legend(fontsize=8)
    fig.suptitle("F07 · Excursion quantile curves · T01 · R3/S3 alignment, 2024–2025");fig.tight_layout();fig.savefig(d/"local_quantiles.png",dpi=140);plt.close(fig)
    fig,axs=plt.subplots(2,3,figsize=(13,8),sharey="row")
    for i,product in enumerate(products):
        g=[r for r in policies if r["product"]==product and r["split"]=="final_evaluation" and r["pair"]=="3" and r["mode"] in colors and r["extension"]=="core" and r["target"]=="3R" and num(r,"fee_USD")==10 and num(r,"slippage_ticks")==1 and num(r,"delay")==0 and r["touch"]=="False" and r["window"]=="main"]
        labels=[r["mode"]+"\n"+r["order_assumption"] for r in g]
        cats=("target_N","stop_N","stop_gap_N","timeout_N","unresolved_missing_path_or_1600_open_N");bottom=np.zeros(len(g))
        for cat,color in zip(cats,("#207b74","#ab6558","#d69a44","#8198b7","#bbbbbb")):
            vals=np.array([num(r,cat) for r in g]);axs[0,i].bar(range(len(g)),vals,bottom=bottom,label=cat.replace("_N",""),color=color);bottom+=vals
        axs[0,i].set_xticks(range(len(g)),labels,fontsize=7);axs[0,i].set_title(product)
        axs[1,i].bar(range(len(g)),[num(r,"completed_session_drawdown_R") for r in g],color="#727980");axs[1,i].set_xticks(range(len(g)),labels,fontsize=7)
    axs[0,0].set_ylabel("Entered trades");axs[1,0].set_ylabel("Observed scorable-session drawdown / R");axs[0,-1].legend(fontsize=7)
    fig.suptitle("F08 · Trade outcomes and ordering-assumption drawdowns · T03 · unknown days omitted");fig.tight_layout();fig.savefig(d/"local_policy_outcomes.png",dpi=140);plt.close(fig)
    if (w/"private/examples_bars.parquet").exists():
        import pandas as pd
        example_bars=pd.read_parquet(w/"private/examples_bars.parquet")
        for product in products:
            cats=("accepted_long","accepted_short","cloud_rejected","losing_15bar","missing_15bar","barrier_ambiguous")
            fig,axs=plt.subplots(3,2,figsize=(13,11))
            for category,ax in zip(cats,axs.flat):
                g=example_bars[(example_bars.example_product==product)&(example_bars.example_category==category)]
                if not len(g):ax.text(.5,.5,"No matching case",ha="center",transform=ax.transAxes);ax.set_title(category);continue
                x=np.arange(len(g));colors_c=np.where(g.close>=g.open,"#207b74","#ab6558")
                ax.vlines(x,g.low,g.high,color=colors_c,linewidth=1);ax.bar(x,np.abs(g.close-g.open),bottom=np.minimum(g.close,g.open),color=colors_c,width=.6)
                ax.plot(x,g.fast,label="EMA20",color="#5575a7",linewidth=.8);ax.plot(x,g.slow,label="EMA50",color="#d69a44",linewidth=.8)
                ax.axhline(g.example_pivot.iloc[0],color="#777",linestyle="--",label="pivot")
                confirm=np.flatnonzero(g.ts.to_numpy()==g.example_confirmation_ts.iloc[0]);
                if len(confirm):ax.axvline(confirm[0],color="#333",linestyle=":",label="confirmation")
                ax.set_title(category+" · "+str(g.day.iloc[0]));ax.set_xlabel("Observed 5m candle index; gaps retained in source ledger");ax.set_ylabel("Unadjusted same-contract price")
            axs[0,0].legend(fontsize=7);fig.suptitle("F09 · "+product+" fixed earliest local examples · private source observations, excluded from website");fig.tight_layout();fig.savefig(d/("local_examples_"+product+".png"),dpi=140);plt.close(fig)
    (w/"figure-environment.json").write_text(json.dumps({"python":__import__("sys").version,"matplotlib":matplotlib.__version__,"numpy":np.__version__,"backend":"Agg","sources":{"horizons.png":"T01","cloud_grid.png":"T01","joint_excursions.png":"T12","threshold_ordering.png":"T09","annual_stability.png":"T04","policy_costs.png":"T03/T13","local_quantiles.png":"T01","local_policy_outcomes.png":"T03","local_examples":"examples.csv and private/examples_bars.parquet, fixed earliest cases, not website assets"}},indent=2)+"\n")

if __name__=="__main__":main()
