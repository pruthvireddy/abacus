"""Summarize saved C1 and ordinary-pair ledgers without rereading source bars."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import NormalDist

import numpy as np
import pandas as pd


WINDOWS = ["asia","london_pre_ny","ny_morning","ny_afternoon","transition"]
Z95 = NormalDist().inv_cdf(.975)
ZFAMILY = NormalDist().inv_cdf(1-.05/(2*70))
METRICS = {"next1":("c3_follows","b3_follows"),
           "next2":("wait_two_success","two_success"),
           "second_given_first":("c4_follows","b4_follows")}


def counts(df: pd.DataFrame, value: str, mask: pd.Series | None = None) -> pd.DataFrame:
    selected = df.loc[mask] if mask is not None else df
    if selected.empty:
        return pd.DataFrame(columns=["n","k"],dtype=float)
    return selected.groupby("session_date")[value].agg(n="size",k="sum").astype(float)


def estimate(data: pd.DataFrame, z: float = Z95) -> dict:
    n = int(data.n.sum())
    k = int(data.k.sum())
    g = len(data)
    if not n:
        return {"numerator":0,"denominator":0,"session_dates":0,"events_per_session":None,
                "probability":None,"ci_low":None,"ci_high":None,"se":None}
    p = k/n
    score = data.k.to_numpy()-p*data.n.to_numpy()
    se = float(np.sqrt(g/(g-1)*np.sum(score**2)/n**2)) if g>1 else None
    return {"numerator":k,"denominator":n,"session_dates":g,
            "events_per_session":n/g,"probability":p,
            "ci_low":max(0,p-z*se) if se is not None else None,
            "ci_high":min(1,p+z*se) if se is not None else None,"se":se}


def contrast(candidate: pd.DataFrame, ordinary: pd.DataFrame) -> dict:
    a,b = estimate(candidate),estimate(ordinary)
    if not a["denominator"] or not b["denominator"]:
        return {"baseline_numerator":b["numerator"],"baseline_denominator":b["denominator"],
                "baseline_session_dates":b["session_dates"],"baseline_events_per_session":b["events_per_session"],
                "baseline_probability":b["probability"],"baseline_ci_low":b["ci_low"],
                "baseline_ci_high":b["ci_high"],"difference_pp":None,
                "difference_ci_low_pp":None,"difference_ci_high_pp":None,
                "family_ci_low_pp":None,"family_ci_high_pp":None}
    pa,pb=a["probability"],b["probability"]
    dates=candidate.index.union(ordinary.index)
    aa=candidate.reindex(dates,fill_value=0)
    bb=ordinary.reindex(dates,fill_value=0)
    score=(aa.k-pa*aa.n)/a["denominator"]-(bb.k-pb*bb.n)/b["denominator"]
    g=len(dates)
    se=float(np.sqrt(g/(g-1)*np.sum(score**2))) if g>1 else None
    delta=100*(pa-pb)
    return {"baseline_numerator":b["numerator"],"baseline_denominator":b["denominator"],
            "baseline_session_dates":b["session_dates"],"baseline_events_per_session":b["events_per_session"],
            "baseline_probability":pb,"baseline_ci_low":b["ci_low"],"baseline_ci_high":b["ci_high"],
            "difference_pp":delta,"difference_ci_low_pp":delta-100*Z95*se if se is not None else None,
            "difference_ci_high_pp":delta+100*Z95*se if se is not None else None,
            "family_ci_low_pp":delta-100*ZFAMILY*se if se is not None else None,
            "family_ci_high_pp":delta+100*ZFAMILY*se if se is not None else None}


def comparison_rows(candidate: pd.DataFrame, ordinary: pd.DataFrame, identity: dict) -> list[dict]:
    rows=[]
    for metric,(candidate_value,ordinary_value) in METRICS.items():
        candidate_mask=candidate.c3_follows if metric=="second_given_first" else None
        ordinary_mask=ordinary.b3_follows if metric=="second_given_first" else None
        ca=counts(candidate,candidate_value,candidate_mask)
        ob=counts(ordinary,ordinary_value,ordinary_mask)
        rows.append({**identity,"metric":metric,**estimate(ca),**contrast(ca,ob)})
    return rows


def simple_rows(data: pd.DataFrame, identity: dict) -> list[dict]:
    metrics={"c2_confirms":("c2_follows",None),
             "immediate_two_per_c1":("immediate_two_success",None),
             "wait_two_per_c1":("wait_two_success",None),
             "c2_old_trend":("c2_old_trend",None),
             "c2_doji":("c2_doji",None),
             "c3_old_given_no_c2":("c3_old_trend",~data.c2_follows)}
    return [{**identity,"metric":name,**estimate(counts(data,value,mask))}
            for name,(value,mask) in metrics.items()]


def price_stats(data: pd.DataFrame, values: np.ndarray, adverse: np.ndarray,
                identity: dict) -> dict:
    n=len(values)
    if not n:
        return {**identity,"events":0,"session_dates":0,"events_per_session":None,
                "mean_signed_ticks":None,"mean_ci_low":None,"mean_ci_high":None,
                "median_signed_ticks":None,"p05_signed_ticks":None,
                "mean_mae_ticks":None,"median_mae_ticks":None,"p90_mae_ticks":None}
    values=np.asarray(values,dtype=float)
    adverse=np.asarray(adverse,dtype=float)
    if not np.isfinite(values).all() or not np.isfinite(adverse).all():
        raise ValueError("nonfinite eligible price path")
    mean=float(values.mean())
    grouped=pd.DataFrame({"session_date":data.session_date.to_numpy(),"score":values-mean}).groupby("session_date").score.sum()
    g=len(grouped)
    se=float(np.sqrt(g/(g-1)*np.sum(grouped.to_numpy()**2)/n**2)) if g>1 else None
    return {**identity,"events":n,"session_dates":g,"events_per_session":n/g,
            "mean_signed_ticks":mean,"mean_ci_low":mean-Z95*se if se is not None else None,
            "mean_ci_high":mean+Z95*se if se is not None else None,
            "median_signed_ticks":float(np.median(values)),
            "p05_signed_ticks":float(np.quantile(values,.05)),
            "mean_mae_ticks":float(adverse.mean()),
            "median_mae_ticks":float(np.median(adverse)),
            "p90_mae_ticks":float(np.quantile(adverse,.90))}


def main() -> None:
    parser=argparse.ArgumentParser()
    parser.add_argument("--stage",required=True,type=Path)
    args=parser.parse_args()
    stage=args.stage.resolve()
    tables=stage/"tables"
    audit=json.loads((stage/"audit.json").read_text())
    output={name:[] for name in ("overall","comparison","period","opportunity_overall",
                                "opportunity_window","opportunity_period","price",
                                "snapback","gc_sensitivity","age2_overall",
                                "age2_comparison","age2_period","price_delta",
                                "prior_bin","prior_bin_opportunity",
                                "snapback_tie_sensitivity")}
    for key in audit["charts"]:
        print("summarize",key,flush=True)
        product,setting_text=key.split("_")
        setting=int(setting_text)
        opportunity=pd.read_parquet(tables/f"opportunities_{key}.parquet")
        ordinary=pd.read_parquet(tables/f"ordinary_{key}.parquet")
        main=opportunity.loc[opportunity.main_prior & opportunity.common_eligible &
                             ~opportunity.gc_gap_excluded].copy()
        candidate=main.loc[main.c2_follows]
        base=ordinary.loc[~ordinary.gc_gap_excluded]
        age2_base=base.loc[base.pair_run_age.eq(2)]
        for direction in (-1,1):
            identity={"product":product,"setting":setting,"direction":direction}
            co=candidate.loc[candidate.direction==direction]
            bo=base.loc[base.direction==direction]
            age2=age2_base.loc[age2_base.direction==direction]
            mo=main.loc[main.direction==direction]
            output["overall"].extend(comparison_rows(co,bo,identity))
            output["age2_overall"].extend(comparison_rows(co,age2,identity))
            output["opportunity_overall"].extend(simple_rows(mo,identity))
            for prior_bin in ("3-4","5-7","8+"):
                bid={**identity,"prior_bin":prior_bin}
                bmain=mo.loc[mo.prior_bin==prior_bin]
                output["prior_bin_opportunity"].extend(simple_rows(bmain,bid))
                output["prior_bin"].extend(comparison_rows(
                    co.loc[co.prior_bin==prior_bin],bo,bid))
            if len(mo):
                immediate=price_stats(mo,mo.immediate_signed_ticks.to_numpy(),
                    mo.immediate_mae_ticks.to_numpy(),{**identity,"policy":"immediate_per_c1"})
                wait_values=np.where(mo.c2_follows,mo.wait_signed_ticks.fillna(0),0)
                wait_adverse=np.where(mo.c2_follows,mo.wait_mae_ticks.fillna(0),0)
                wait_all=price_stats(mo,wait_values,wait_adverse,
                    {**identity,"policy":"wait_per_c1"})
                wait_cond=price_stats(co,co.wait_signed_ticks.to_numpy(),co.wait_mae_ticks.to_numpy(),
                    {**identity,"policy":"wait_confirmed"})
                output["price"].extend([immediate,wait_all,wait_cond])
                delta=price_stats(mo,wait_values-mo.immediate_signed_ticks.to_numpy(),
                    np.zeros(len(mo)),{**identity,"policy":"wait_minus_immediate_per_c1"})
                output["price_delta"].append({k:v for k,v in delta.items() if k not in
                    {"mean_mae_ticks","median_mae_ticks","p90_mae_ticks"}})
            for window in WINDOWS:
                cid={**identity,"decision_window":window}
                cwin=co.loc[co.decision_window==window]
                bwin=bo.loc[bo.decision_window==window]
                age2win=age2.loc[age2.decision_window==window]
                output["comparison"].extend(comparison_rows(cwin,bwin,cid))
                output["age2_comparison"].extend(comparison_rows(cwin,age2win,cid))
                output["opportunity_window"].extend(simple_rows(
                    mo.loc[mo.c1_window==window],{**identity,"c1_window":window}))
                for block in ("early","middle","recent"):
                    output["period"].extend(comparison_rows(cwin.loc[cwin.block==block],
                        bwin.loc[bwin.block==block],{**cid,"block":block})[:2])
                    output["age2_period"].extend(comparison_rows(cwin.loc[cwin.block==block],
                        age2win.loc[age2win.block==block],{**cid,"block":block})[:2])
            for block in ("early","middle","recent"):
                output["opportunity_period"].extend(simple_rows(mo.loc[mo.block==block],
                    {**identity,"block":block}))
            if product in {"ES","GC","NQ"} and key in {"ES_4","ES_5","GC_6","NQ_10"}:
                snap_all=opportunity.loc[opportunity.prior_run.eq(1) & opportunity.common_eligible &
                    opportunity.larger_context.eq("aligned") &
                    ~opportunity.gc_gap_excluded & opportunity.direction.eq(direction)]
                snap=snap_all.loc[~snap_all.larger_equal_second_tie]
                confirmed=snap.loc[snap.c2_follows]
                output["snapback"].extend(simple_rows(snap,{**identity,"context":"onebar_aligned"})[:3])
                output["snapback"].extend(comparison_rows(confirmed,bo,{**identity,"context":"onebar_aligned"})[:2])
                for label,sample in (("strict_no_ties",snap),
                                     ("include_equal_second",snap_all),
                                     ("ties_only",snap_all.loc[snap_all.larger_equal_second_tie])):
                    confirmed_sample=sample.loc[sample.c2_follows]
                    output["snapback_tie_sensitivity"].append({**identity,
                        "sensitivity":label,"metric":"c2_confirms",
                        **estimate(counts(sample,"c2_follows"))})
                    output["snapback_tie_sensitivity"].append({**identity,
                        "sensitivity":label,"metric":"next2",
                        **estimate(counts(confirmed_sample,"wait_two_success"))})
            if product=="GC":
                for label,excluded in (("gap_excluded",True),("gap_included",False)):
                    all_main=opportunity.loc[opportunity.main_prior & opportunity.common_eligible &
                        opportunity.direction.eq(direction)]
                    if excluded:
                        all_main=all_main.loc[~all_main.gc_gap_excluded]
                    confirmed=all_main.loc[all_main.c2_follows]
                    output["gc_sensitivity"].append({**identity,"sensitivity":label,
                        "metric":"next2",**estimate(counts(confirmed,"wait_two_success"))})
        del opportunity,ordinary,main,candidate,base
    for name,rows in output.items():
        pd.DataFrame(rows).to_csv(tables/f"{name}.csv",index=False)
    comparison=pd.read_csv(tables/"comparison.csv")
    periods=pd.read_csv(tables/"period.csv")
    screen=comparison.loc[comparison.metric=="next2"].copy()
    screen["supported"] = ((screen.denominator>=300) & (screen.session_dates>=100) &
                           (screen.events_per_session>=2))
    consistent=[]
    for _,row in screen.iterrows():
        selected=periods.loc[(periods["product"]==row["product"]) &
            (periods.setting==row.setting) & (periods.direction==row.direction) &
            (periods.decision_window==row.decision_window) & periods.metric.eq("next2")]
        consistent.append(len(selected)==3 and (selected.session_dates>=30).all() and
                          (selected.difference_pp>0).all())
    screen["three_period_positive"]=consistent
    screen["noteworthy_positive"]=screen.supported & (screen.family_ci_low_pp>0) & screen.three_period_positive
    screen.to_csv(tables/"headline_screen.csv",index=False)
    print("noteworthy",int(screen.noteworthy_positive.sum()),"of",len(screen),flush=True)


if __name__=="__main__":main()
