"""Derive every displayed probability from the saved event ledgers."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import NormalDist

import numpy as np
import pandas as pd


METRICS = {
    "p1": ("c2_follows", "primary_eligible"),
    "p2": ("c2_c3_follow", "primary_eligible"),
    "p3_given_p1": ("c3_follows", "c2_conditional"),
    "p3_more": ("c2_c3_c4_follow", "three_eligible"),
    "immediate_resumption": ("immediate_resumption", "primary_eligible"),
    "c2_doji": ("c2_doji", "primary_eligible"),
    "c3_doji": ("c3_doji", "primary_eligible"),
}
Z95 = NormalDist().inv_cdf(.975)
ZFAMILY = NormalDist().inv_cdf(1-.05/(2*210))


def session_counts(df: pd.DataFrame, metric: str) -> pd.DataFrame:
    value, eligible = METRICS[metric]
    mask = df["primary_eligible"] & df["c2_follows"] if eligible == "c2_conditional" else df[eligible]
    subset = df.loc[mask, ["session_date",value]]
    if subset.empty: return pd.DataFrame(columns=["n","k"])
    return subset.groupby("session_date")[value].agg(n="size",k="sum").astype(float)


def estimate(counts: pd.DataFrame, z: float = Z95) -> dict:
    n = int(counts.n.sum())
    k = int(counts.k.sum())
    g = len(counts)
    if not n: return {"numerator":0,"denominator":0,"session_dates":0,
                      "events_per_session":None,"probability":None,"ci_low":None,"ci_high":None,"se":None}
    p = k/n
    score = counts.k.to_numpy() - p*counts.n.to_numpy()
    se = float(np.sqrt((g/(g-1) if g>1 else 0)*np.sum(score**2)/n**2)) if g>1 else None
    return {"numerator":k,"denominator":n,"session_dates":g,
            "events_per_session":n/g,"probability":p,
            "ci_low":max(0,p-z*se) if se is not None else None,
            "ci_high":min(1,p+z*se) if se is not None else None,"se":se}


def difference(a: pd.DataFrame, b: pd.DataFrame, z: float = Z95) -> dict:
    ea, eb = estimate(a), estimate(b)
    if not ea["denominator"] or not eb["denominator"]:
        return {"baseline_probability":None,"baseline_numerator":None,"baseline_denominator":None,
                "difference_pp":None,"difference_ci_low_pp":None,"difference_ci_high_pp":None,
                "family_ci_low_pp":None,"family_ci_high_pp":None}
    pa,pb = ea["probability"],eb["probability"]
    dates = a.index.union(b.index)
    aa,bb = a.reindex(dates,fill_value=0),b.reindex(dates,fill_value=0)
    score = (aa.k-pa*aa.n)/ea["denominator"] - (bb.k-pb*bb.n)/eb["denominator"]
    g = len(dates)
    se = float(np.sqrt(g/(g-1)*np.sum(score**2))) if g>1 else None
    delta = 100*(pa-pb)
    return {"baseline_probability":pb,"baseline_numerator":eb["numerator"],
            "baseline_denominator":eb["denominator"],"difference_pp":delta,
            "difference_ci_low_pp":delta-100*z*se if se is not None else None,
            "difference_ci_high_pp":delta+100*z*se if se is not None else None,
            "family_ci_low_pp":delta-100*ZFAMILY*se if se is not None else None,
            "family_ci_high_pp":delta+100*ZFAMILY*se if se is not None else None}


def summarized(df: pd.DataFrame, group: list[str], *, baseline_keys: list[str] | None = None,
               metrics: tuple[str,...] = tuple(METRICS)) -> pd.DataFrame:
    rows = []
    bases = {}
    if baseline_keys is not None:
        for key, sub in df.groupby(baseline_keys, observed=True):
            if not isinstance(key,tuple): key=(key,)
            bases[key] = {m:session_counts(sub,m) for m in metrics}
    for key,sub in df.groupby(group,observed=True):
        if not isinstance(key,tuple): key=(key,)
        row0 = dict(zip(group,key))
        bkey = tuple(row0[k] for k in baseline_keys) if baseline_keys else None
        for metric in metrics:
            counts=session_counts(sub,metric)
            row={**row0,"metric":metric,**estimate(counts)}
            if bkey is not None:
                row.update(difference(counts,bases[bkey][metric]))
            rows.append(row)
    return pd.DataFrame(rows)


def strict_larger_cohort(df: pd.DataFrame) -> pd.DataFrame:
    """Keep only unambiguous, strictly earlier completed larger-chart states."""
    return df.loc[df.larger_context.ne("unavailable") & ~df.larger_equal_second_tie]


def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--stage",required=True,type=Path); args=ap.parse_args()
    stage=args.stage.resolve(); tables=stage/"tables"
    if not (stage/"audit.json").is_file(): raise FileNotFoundError("extraction not complete")
    audit=json.loads((stage/"audit.json").read_text())
    collected={k:[] for k in ("overall","lookup","period","structure","larger","larger_aggregate","onebar_larger","sensitivity","run_lengths")}
    features=["body_ge_70","close_loc_ge_80","adverse_wick_lt_20","break_prev_extreme",
              "prior_opposing_wick_lt_20","prior_net_units_per_bar_ge_075","prior_pace_lt_60s"]
    for key in audit["charts"]:
        print("summarize",key,flush=True)
        raw=pd.read_parquet(tables/f"events_{key}.parquet")
        primary=raw.loc[~raw.gc_gap_excluded & raw.session_window.ne("unavailable")].copy()
        collected["overall"].append(summarized(primary,["product","setting","direction"],metrics=tuple(METRICS)))
        collected["lookup"].append(summarized(primary,["product","setting","direction","prior_bin","session_window"],
                                             baseline_keys=["product","setting","direction","session_window"]))
        collected["period"].append(summarized(primary,["product","setting","direction","prior_bin","session_window","block"],
                                             baseline_keys=["product","setting","direction","session_window","block"],
                                             metrics=("p2",)))
        struct=[]
        for feature in features:
            grouped=summarized(primary,["product","setting","direction","prior_bin","session_window",feature],
                               baseline_keys=["product","setting","direction","prior_bin","session_window"],
                               metrics=("p2",))
            grouped["feature"]=feature
            grouped["feature_value"]=grouped[feature]
            grouped=grouped.drop(columns=[feature])
            struct.append(grouped)
        collected["structure"].append(pd.concat(struct,ignore_index=True))
        if raw.larger_context.ne("unavailable").any():
            paired = strict_larger_cohort(primary)
            collected["larger"].append(summarized(paired,
                ["product","setting","direction","prior_bin","session_window","larger_context"],
                baseline_keys=["product","setting","direction","prior_bin","session_window"],metrics=("p1","p2")))
            collected["larger_aggregate"].append(summarized(paired,
                ["product","setting","direction","prior_bin","larger_context"],
                baseline_keys=["product","setting","direction","prior_bin"],metrics=("p1","p2")))
            one=paired.loc[paired.prior_run.eq(1)]
            collected["onebar_larger"].append(summarized(one,
                ["product","setting","direction","larger_context"],
                baseline_keys=["product","setting","direction"],metrics=("p1","p2")))
            # Ties are excluded from primary paired estimates; the last strictly
            # earlier state is used when they are reintroduced as sensitivity.
            strict=paired.loc[paired.primary_eligible]
            tied=primary.loc[primary.primary_eligible & primary.larger_equal_second_tie &
                             primary.larger_context.ne("unavailable")]
            same=paired.loc[paired.c1_same_second & paired.horizon_complete].assign(primary_eligible=True)
            both=primary.loc[primary.c1_same_second & primary.horizon_complete &
                             primary.larger_equal_second_tie & primary.larger_context.ne("unavailable")].assign(primary_eligible=True)
            for name,sub in [("strict_larger",strict),
                             ("include_larger_equal_second",pd.concat([strict,tied])),
                             ("include_c1_same_second",pd.concat([strict,same])),
                             ("include_both_ambiguities",pd.concat([strict,tied,same,both]))]:
                for context,part in sub.groupby("larger_context"):
                    est=estimate(session_counts(part,"p2"))
                    collected["sensitivity"].append(pd.DataFrame([{"product":key.split('_')[0],
                        "setting":int(key.split('_')[1]),"sensitivity":name,"larger_context":context,
                        "same_second_signal_excluded":len(same)+len(both),
                        "eligible_ties_reintroduced":len(tied),
                        "larger_equal_second_ties":int(primary.larger_equal_second_tie.sum()),**est}]))
        if key.startswith("GC"):
            base=primary.loc[primary.primary_eligible]
            all_=raw.loc[raw.primary_eligible]
            for name,sub in [("gc_gap_excluded",base),("gc_gap_included",all_)]:
                est=estimate(session_counts(sub,"p2"))
                collected["sensitivity"].append(pd.DataFrame([{"product":"GC","setting":int(key.split('_')[1]),
                    "sensitivity":name,**est}]))
        exact=[]
        for direction,one_direction in primary.loc[primary.primary_eligible].groupby("direction"):
            lengths=one_direction[["subsequent_run_length","run_censored"]].drop_duplicates()
            for _,length in lengths.iterrows():
                matched=(one_direction.subsequent_run_length.eq(length.subsequent_run_length) &
                         one_direction.run_censored.eq(length.run_censored))
                counts=one_direction.assign(matched=matched).groupby("session_date").matched.agg(n="size",k="sum")
                exact.append({"product":key.split('_')[0],"setting":int(key.split('_')[1]),
                    "direction":direction,"subsequent_run_length":int(length.subsequent_run_length),
                    "run_censored":bool(length.run_censored),
                    "session_dates_with_events":int(one_direction.loc[matched,"session_date"].nunique()),
                    **estimate(counts)})
        collected["run_lengths"].append(pd.DataFrame(exact))
        del raw,primary
    for name,parts in collected.items():
        if parts: pd.concat(parts,ignore_index=True).to_csv(tables/f"{name}.csv",index=False)
    lookup=pd.read_csv(tables/"lookup.csv")
    period=pd.read_csv(tables/"period.csv")
    p2=lookup.loc[lookup.metric.eq("p2")].copy()
    p2["supported"]=(p2.denominator>=300)&(p2.session_dates>=100)&(p2.events_per_session>=2)
    stable=[]
    for _,r in p2.iterrows():
        sub=period.loc[(period["product"]==r["product"])&(period["setting"]==r["setting"])&
            (period["direction"]==r["direction"])&(period["prior_bin"]==r["prior_bin"])&
            (period["session_window"]==r["session_window"])]
        stable.append(len(sub)==3 and (sub.session_dates>=30).all() and (sub.difference_pp>0).all())
    p2["three_block_positive"]=stable
    p2["noteworthy_positive"]=(p2.prior_bin.ne("1-2")&p2.supported&
            (p2.family_ci_low_pp>0)&p2.three_block_positive)
    p2.to_csv(tables/"headline_screen.csv",index=False)
    print("noteworthy",int(p2.noteworthy_positive.sum()),"of",len(p2),flush=True)


if __name__=="__main__": main()
